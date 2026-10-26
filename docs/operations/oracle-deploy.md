# Deploying Socrat to an Oracle Cloud VM

Single-host production: PostgreSQL, API, worker, web, the Playground visual checker and Caddy (automatic HTTPS) run from `infra/runtime/production/compose.yaml`. Delivery is fully automated:

```
push to main ─► continuous-integration (lint, tests, scans, build)
              └► publish-images  → ghcr.io/<owner>/socrat-{api,web,explainer}:sha-<commit> (multi-arch, attested)
                    └► deploy-production (workflow_run, `production` environment, reviewer gate)
                          └► SSH → /opt/socrat/runtime/deploy-production.sh
                                 pull by digest → migrate → up --wait → HTTPS health gate → promote | roll back
```

## Hard requirements

1. **Two DNS names on two different registrable domains.** `APP_HOST` (the site) and `SANDBOX_HOST` (signed Playground frames), for example `socrat.app` and `socrat-visuals.net`. The API refuses to enable the Playground when both share a registrable domain, because generated visuals must not be able to reach the app's cookies. Both point at the VM's public IP.
2. **An OIDC provider** (Google, Microsoft, Auth0, …). Production has no developer login. The redirect URI to register is `https://<APP_HOST>/api/v1/auth/callback`.
3. **An AI provider key** for the tutor and Playground: an OpenAI API key (recommended, with `gpt-5.4-mini`), any OpenAI-compatible endpoint, or Anthropic. It goes in the `ai_api_key` secret file.
4. **Python and C++ run in the learner's browser** (`SOCRAT_BROWSER_RUNTIMES='["python","cpp"]'`, the default); nothing executes on the VM. The web image copies the runtimes (about 115 MB) into `public/runtimes/` at build time, served with immutable caching. If a proxy sits in front of the web container, it must pass `/runner/*` and `/runtimes/*` through unchanged (including their `Content-Security-Policy` and `Cache-Control` headers) and allow responses of about 80 MB. Java needs the gVisor runner host described in `infra/execution/` and `docs/security/`; never enable the `local_process` backend on an internet-facing host.
5. **LLM budgets:** set `SOCRAT_AI_PRICE_INPUT_PER_MTOK` / `SOCRAT_AI_PRICE_OUTPUT_PER_MTOK` to your provider's prices and adjust the `SOCRAT_AI_*_BUDGET_USD` caps; `SOCRAT_AI_ENABLED=false` switches every model call off. Optional `SOCRAT_SENTRY_DSN` forwards server errors to Sentry or GlitchTip.

## One-time VM setup

Provision the VM with the existing Terraform (`infra/oci/`, `VM.Standard.A1.Flex`, Ubuntu) or by hand. Its cloud-init installs Docker and Compose v2 and creates `/opt/socrat/runtime`, `/opt/socrat/secrets` and `/var/lib/socrat/releases` for the `ubuntu` user. Then:

```bash
# 1. Open 80/tcp, 443/tcp and 443/udp in the OCI security list / NSG, and in the host firewall:
sudo iptables -I INPUT -p tcp --dport 80  -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT -p udp --dport 443 -j ACCEPT
sudo netfilter-persistent save

# 2. Secret files (mode 0600, one non-empty line each; never commit these):
cd /opt/socrat/secrets
umask 077
openssl rand -base64 48 | tr -d '\n' > postgres_password
openssl rand -base64 64 | tr -d '\n' > session_secret            # >= 48 chars
openssl rand -base64 48 | tr -d '\n' > metrics_token             # >= 32 chars
openssl rand -base64 48 | tr -d '\n' > explainer_checker_secret  # >= 32 chars
printf '%s' 'YOUR_OIDC_CLIENT_SECRET' > oidc_client_secret
printf '%s' 'YOUR_RAZORPAY_KEY_SECRET' > razorpay_key_secret          # Razorpay -> Settings -> API Keys
printf '%s' 'YOUR_RAZORPAY_WEBHOOK_SECRET' > razorpay_webhook_secret  # the secret you set on the webhook
printf '%s' 'YOUR_AI_PROVIDER_API_KEY' > ai_api_key
printf '%s' 'YOUR_RESEND_API_KEY' > resend_api_key             # Resend -> API Keys (sending access)
chmod 600 *

# 3. The deploy user must be in the docker group (cloud-init does this for `ubuntu`).
```

Generate a deploy key pair for CI (`ssh-keygen -t ed25519 -f socrat-deploy -N ''`), append `socrat-deploy.pub` to `~/.ssh/authorized_keys` on the VM, and keep the private key for the GitHub secret below. Capture the host key with `ssh-keyscan -t ed25519 <ORACLE_HOST>`.

## GitHub configuration

Create a **`production` environment** (Settings → Environments) and add required reviewers. Then:

### Repository / environment **secrets**

| Name | Value |
| --- | --- |
| `ORACLE_HOST` | VM public IP or DNS name |
| `ORACLE_USER` | SSH user, e.g. `ubuntu` |
| `ORACLE_SSH_KEY` | private deploy key (full PEM/OpenSSH text) |
| `ORACLE_KNOWN_HOSTS` | output of `ssh-keyscan -t ed25519 <ORACLE_HOST>` |

`GITHUB_TOKEN` is provided automatically and is used both to publish images and, over SSH stdin, for `docker login ghcr.io` on the VM.

### Repository / environment **variables** (non-secret)

| Name | Required | Example / meaning |
| --- | --- | --- |
| `APP_HOST` | yes | `socrat.app` |
| `SANDBOX_HOST` | yes | `socrat-visuals.net` (different registrable domain) |
| `TLS_EMAIL` | yes | `ops@socrat.app` (certificate expiry notices) |
| `SOCRAT_SANDBOX_ORIGIN` | yes | `https://socrat-visuals.net`. **Baked into the web image at CI build time** (CSP `frame-src`), so set it before the first build |
| `SOCRAT_OIDC_ISSUER` | yes | `https://accounts.google.com` |
| `SOCRAT_OIDC_CLIENT_ID` | yes | OIDC client id |
| `SOCRAT_BILLING_ENABLED` | for paid plans | `true` turns on Free/Plus/Pro limits and checkout; default `false` |
| `SOCRAT_RAZORPAY_KEY_ID` | for paid plans | Razorpay Key ID (`rzp_live_...`). Public, so a variable, not a secret |
| `SOCRAT_EMAIL_FROM` | for email sign-in | `Socrat <no-reply@your-verified-domain>`; email sign-in stays hidden until this and the `resend_api_key` secret are set |
| `SOCRAT_AI_PROVIDER` | recommended | `openai` (any OpenAI-compatible endpoint) or `anthropic`; default `openai` |
| `SOCRAT_OPENAI_BASE_URL` | only for compatible endpoints | leave unset for api.openai.com; e.g. a vLLM or Nebius `/v1/` URL |
| `SOCRAT_OPENAI_MODEL` | yes for `openai` | `gpt-5.4-mini` (tutor, lessons, trial and Playground) |
| `SOCRAT_EXPLAINER_MODEL` | optional | Playground model id (defaults to the tutor model) |
| `SOCRAT_EXPLAINER_CHAT_TEMPLATE_KWARGS` | compatible endpoints only | `{"enable_thinking": false}` for Qwen3; ignored for api.openai.com |
| `SOCRAT_AI_PRICE_INPUT_PER_MTOK` / `SOCRAT_AI_PRICE_OUTPUT_PER_MTOK` | recommended | the model's prices; default GPT-5.4 mini: `0.75` / `4.5` |
| `SOCRAT_AI_DAILY_BUDGET_USD` / `SOCRAT_AI_MONTHLY_BUDGET_USD` | recommended | site-wide caps; defaults `25` / `400` |
| `SOCRAT_AI_USER_DAILY_BUDGET_USD` | optional | per-learner tutor cap (the Playground uses plan counts); default `0.5` |
| `SOCRAT_CONTENT_ADMIN_IDENTITIES` | optional | JSON list of `"issuer\|subject"` allowed to review content |
| `SOCRAT_ADMIN_SUBJECTS` | optional | JSON list of OIDC subjects allowed into `/admin` |

## Final environment of the running API (rendered by `compose.yaml`)

For reference, this is what the production API container receives. Everything is set by the compose file; do not hand-edit on the host.

| Variable | Source | Notes |
| --- | --- | --- |
| `SOCRAT_ENVIRONMENT` | fixed `production` | enables the secure-mode validations |
| `SOCRAT_PUBLIC_ORIGIN` | `https://$APP_HOST` | must be HTTPS, no trailing slash |
| `SOCRAT_DATABASE_HOST/PORT/NAME/USER` | fixed | `postgres:5432`, db/user `socrat` |
| `SOCRAT_DATABASE_PASSWORD_FILE` | secret file | `/run/secrets/postgres_password` |
| `SOCRAT_SESSION_SECRET_FILE` | secret file | ≥ 48 characters |
| `SOCRAT_DEV_LOGIN_ENABLED` | fixed `false` | developer login is refused in production |
| `SOCRAT_OIDC_ISSUER`, `SOCRAT_OIDC_CLIENT_ID` | variables | |
| `SOCRAT_OIDC_CLIENT_SECRET_FILE` | secret file | |
| `SOCRAT_METRICS_TOKEN_FILE` | secret file | ≥ 32 characters; `/api/metrics` is hidden by Caddy |
| `SOCRAT_AI_PROVIDER`, `SOCRAT_OPENAI_BASE_URL`, `SOCRAT_OPENAI_MODEL` | variables | |
| `SOCRAT_OPENAI_API_KEY_FILE` | secret file `ai_api_key` | new `_FILE` support added in `config.py` |
| `SOCRAT_EXPLAINER_ENABLED`, `…_MODEL`, `…_CHAT_TEMPLATE_KWARGS`, `…_DAILY_MESSAGES` | variables / defaults | |
| `SOCRAT_EXPLAINER_SANDBOX_ORIGIN` | `https://$SANDBOX_HOST` | must differ in registrable domain from the app |
| `SOCRAT_EXPLAINER_CHECKER_URL` | fixed | `http://explainer-checker:8010/check` (private network) |
| `SOCRAT_EXPLAINER_CHECKER_SECRET_FILE` | secret file | ≥ 32 characters, shared with the checker container |
| `SOCRAT_*_ENABLED` feature flags | fixed `true` | onboarding, diagnostics, planning, sessions, assessments, dashboard, reminders, tutor |
| `SOCRAT_EXECUTION_ENABLED` | fixed `false` | see "Hard requirements" |

Variables that are **only for local development** and must never be set in production: `SOCRAT_DEMO_MODE`, `SOCRAT_DEV_LOGIN_ENABLED=true`, `SOCRAT_EXECUTION_BACKEND=local_process|demo_docker`, any `*_API_KEY` or `*_SECRET` as a plain value, and the staging-only placeholders in `.env` (`visuals.example.net`, `explainer-checker` hostname for native runs).

## First deploy

1. Point both DNS records at the VM and wait for propagation (Caddy needs both to issue certificates).
2. Set the secrets and variables above, then **push to `main`** (or run *deploy-production* manually with a commit that already has published images).
3. Approve the `production` environment deployment. The workflow uploads the runtime, logs the VM into GHCR, and runs the health-gated deploy.
4. Verify:
   ```bash
   curl -fsS https://$APP_HOST/api/health/ready      # {"status":"ready"}
   curl -sI  https://$SANDBOX_HOST/                  # 404 (frames are served only with a signed URL)
   ```
   Then sign in, open the Playground and generate a visual.

## Operations

- **Rollback:** a failed health gate rolls back automatically. To roll back manually, on the VM run `docker compose --project-name socrat --env-file /var/lib/socrat/releases/previous.env --file /opt/socrat/runtime/compose.yaml up -d --wait`, or re-run *deploy-production* with an older commit.
- **Logs:** `docker compose --project-name socrat --file /opt/socrat/runtime/compose.yaml logs -f api`. Playground failures are logged by the `socrat.explainer` logger.
- **Backups:** reuse `scripts/operations/backup-postgres.sh` against project `socrat` on a schedule, and copy the archive to the OCI Object Storage bucket from `infra/oci`.
- **Rotating a secret:** replace the file in `/opt/socrat/secrets` and re-run the deploy (containers re-read secrets on recreate).
- **Observability:** Prometheus and Grafana are in `infra/runtime/staging/` and can be added to the production compose later; they are omitted here to fit the Always-Free 12 GB budget.
