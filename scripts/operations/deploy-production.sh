#!/usr/bin/env bash
# Health-gated production deploy for the single-host Oracle VM runtime.
#
# Run on the VM (the CD workflow copies this file and infra/runtime/production/ there and calls it
# over SSH). Non-secret release inputs arrive as environment variables; secrets already live as
# files under SOCRAT_SECRETS_DIR and are never passed on the command line or written to the release env.
set -euo pipefail

RUNTIME_DIR="${SOCRAT_RUNTIME_DIR:-/opt/socrat/runtime}"
STATE_DIR="${SOCRAT_STATE_DIR:-/var/lib/socrat/releases}"
export SOCRAT_SECRETS_DIR="${SOCRAT_SECRETS_DIR:-/opt/socrat/secrets}"
PROJECT="socrat"
DOCKER="${SOCRAT_DOCKER:-docker}"          # set to "sudo docker" when the deploy user is not in the docker group
files=(--file "$RUNTIME_DIR/compose.yaml")
# A host that already runs nginx/certbot on 80/443 uses the loopback overlay instead of Caddy.
if [[ "${SOCRAT_HOST_PROXY:-}" == "1" ]]; then files+=(--file "$RUNTIME_DIR/compose.host-proxy.yaml"); fi
HEALTH_URL="${SOCRAT_HEALTH_URL:-}"

fail() { echo "deploy: $*" >&2; exit 1; }

required=(RELEASE_SHA SOCRAT_API_IMAGE SOCRAT_WEB_IMAGE SOCRAT_EXPLAINER_IMAGE APP_HOST SANDBOX_HOST TLS_EMAIL SOCRAT_OIDC_ISSUER SOCRAT_OIDC_CLIENT_ID)
optional=(SOCRAT_AI_PROVIDER SOCRAT_OPENAI_BASE_URL SOCRAT_OPENAI_MODEL SOCRAT_AI_TIMEOUT_SECONDS SOCRAT_EXPLAINER_ENABLED SOCRAT_EXPLAINER_MODEL SOCRAT_EXPLAINER_CHAT_TEMPLATE_KWARGS SOCRAT_EXPLAINER_DAILY_MESSAGES SOCRAT_CONTENT_ADMIN_IDENTITIES SOCRAT_ADMIN_SUBJECTS SOCRAT_TUTOR_MODEL_ENABLED SOCRAT_BILLING_ENABLED SOCRAT_RAZORPAY_KEY_ID)

for name in "${required[@]}"; do
  [[ -n "${!name:-}" ]] || fail "$name is required"
done
[[ "$RELEASE_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "RELEASE_SHA must be a full lowercase Git SHA"
for name in SOCRAT_API_IMAGE SOCRAT_WEB_IMAGE SOCRAT_EXPLAINER_IMAGE; do
  [[ "${!name}" =~ ^ghcr\.io/[a-z0-9._/-]+(@sha256:[0-9a-f]{64}|:[A-Za-z0-9._-]+)$ ]] || fail "$name must be a lowercase ghcr.io reference"
done
[[ "$APP_HOST" != "$SANDBOX_HOST" ]] || fail "APP_HOST and SANDBOX_HOST must differ (and use different registrable domains)"

for secret in postgres_password session_secret oidc_client_secret metrics_token ai_api_key explainer_checker_secret razorpay_key_secret razorpay_webhook_secret; do
  file="$SOCRAT_SECRETS_DIR/$secret"
  [[ -s "$file" ]] || fail "missing secret file $file"
  # Containers run as non-root users, so the files are world-readable; the directory (0700) is the boundary.
  case "$(stat -c '%a' "$file")" in 400|440|444|600|640|644) ;; *) fail "$file has an unsafe mode" ;; esac
done
[[ "$(stat -c '%a' "$SOCRAT_SECRETS_DIR")" == "700" ]] || fail "$SOCRAT_SECRETS_DIR must be mode 0700"

mkdir -p "$STATE_DIR"
env_file="$STATE_DIR/$RELEASE_SHA.env"
umask 077
{
  for name in "${required[@]}" SOCRAT_SECRETS_DIR; do
    value="${!name}"
    [[ "$value" != *"'"* && "$value" != *$'\n'* ]] || fail "$name contains a quote or newline"
    printf "%s='%s'\n" "$name" "$value"
  done
  for name in "${optional[@]}"; do
    value="${!name:-}"
    [[ -z "$value" ]] && continue
    [[ "$value" != *"'"* && "$value" != *$'\n'* ]] || fail "$name contains a quote or newline"
    printf "%s='%s'\n" "$name" "$value"
  done
} > "$env_file"

compose() { $DOCKER compose --project-name "$PROJECT" --env-file "$1" "${files[@]}" "${@:2}"; }
health() {
  for _ in $(seq 1 24); do
    if curl -fsS --max-time 10 "${HEALTH_URL:-https://$APP_HOST/api/health/ready}" | grep -q '"ready"'; then return 0; fi
    sleep 5
  done
  return 1
}

previous=""
[[ -L "$STATE_DIR/current.env" ]] && previous="$(readlink -f "$STATE_DIR/current.env")"

compose "$env_file" config --quiet
if [[ "${SOCRAT_SKIP_PULL:-}" != "1" ]]; then compose "$env_file" pull; fi
if compose "$env_file" up --detach --remove-orphans --wait --wait-timeout 300 && health; then
  ln -sfn "$env_file" "$STATE_DIR/current.env"
  [[ -n "$previous" ]] && ln -sfn "$previous" "$STATE_DIR/previous.env"
  $DOCKER image prune --force --filter "until=168h" >/dev/null || true
  echo "deploy: release $RELEASE_SHA promoted"
  exit 0
fi

echo "deploy: release $RELEASE_SHA failed its health gate" >&2
compose "$env_file" logs --tail 80 api web explainer-checker caddy >&2 || true
if [[ -n "$previous" && -f "$previous" ]]; then
  echo "deploy: rolling back to $(basename "$previous" .env)" >&2
  compose "$previous" up --detach --remove-orphans --wait --wait-timeout 300 || true
fi
exit 1
