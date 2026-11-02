from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlparse

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_SESSION_SECRET = "local-development-only-change-before-deploy"
LOCAL_DATABASE_URL = "sqlite:///socrat.local.db"


def _read_secret_file(name: str, file_name: str) -> str:
    path = Path(file_name)
    try:
        if not path.is_file() or path.stat().st_size > 16_384:
            raise ValueError(f"{name}_file must reference a small regular file")
        value = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"{name}_file could not be read") from exc

    if value.endswith("\n"):
        value = value[:-1]
        if value.endswith("\r"):
            value = value[:-1]
    if not value or "\n" in value or "\r" in value:
        raise ValueError(f"{name}_file must contain one non-empty single line")
    return value


def _secret_from_file(name: str, direct: SecretStr, file_name: str, default: str = ""):
    direct_value = direct.get_secret_value()
    if not file_name:
        return direct
    if direct_value not in {"", default}:
        raise ValueError(f"{name} cannot be provided both directly and by file")
    value = _read_secret_file(name, file_name)
    return SecretStr(value)


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SOCRAT_", env_file=".env", extra="ignore")
    database_url: SecretStr = SecretStr(LOCAL_DATABASE_URL)
    database_host: str = ""
    database_port: int = 5432
    database_name: str = ""
    database_user: str = ""
    database_password_file: str = ""

    @model_validator(mode="after")
    def load_database_password(self):
        if not self.database_password_file:
            return self
        if self.database_url.get_secret_value() != LOCAL_DATABASE_URL:
            raise ValueError("database_url and database_password_file cannot both be provided")
        if not self.database_host or not self.database_name or not self.database_user:
            raise ValueError(
                "database_host, database_name and database_user are required with a password file"
            )
        if not 1 <= self.database_port <= 65535:
            raise ValueError("database_port must be between 1 and 65535")
        password = _read_secret_file("database_password", self.database_password_file)
        user = quote(self.database_user, safe="")
        encoded_password = quote(password, safe="")
        database = quote(self.database_name, safe="")
        self.database_url = SecretStr(
            f"postgresql+psycopg://{user}:{encoded_password}"
            f"@{self.database_host}:{self.database_port}/{database}"
        )
        return self

    @property
    def database_url_value(self) -> str:
        return self.database_url.get_secret_value()


class Settings(DatabaseSettings):
    environment: Literal["development", "test", "staging", "production"] = "development"
    public_origin: str = "http://localhost:3000"
    session_secret: SecretStr = SecretStr(LOCAL_SESSION_SECRET)
    session_secret_file: str = ""
    session_ttl_seconds: int = 30 * 86400
    dev_login_enabled: bool = False
    # Local browser runs wait for the catalog and quiz bank before accepting requests.
    prewarm_content: bool = False
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: SecretStr = SecretStr("")
    oidc_client_secret_file: str = ""
    metrics_token: SecretStr = SecretStr("")
    metrics_token_file: str = ""

    # Code judge. "local_process" is an insecure native runner for development only;
    # deployed environments use gVisor workers with attested images.
    execution_backend: Literal["gvisor_docker", "local_process", "demo_docker"] = "gvisor_docker"
    execution_signing_secret: SecretStr = SecretStr("")
    execution_worker_secret: SecretStr = SecretStr("")
    execution_signing_secret_file: str = ""
    execution_worker_secret_file: str = ""
    execution_profiles: list[dict] = Field(default_factory=list, max_length=3)
    execution_daily_quota: int = Field(default=400, ge=1, le=5000)
    execution_queue_limit: int = Field(default=3, ge=1, le=20)
    # In-browser execution (Pyodide for Python, Clang/WASI for C++). The learner's browser runs
    # the code and reports output digests; the server compares them with the expected outputs,
    # which never leave it. Languages listed here skip the worker queue.
    browser_runtimes: list[Literal["python", "cpp"]] = Field(
        default=["python", "cpp"], max_length=2
    )

    # Socrat assistant. Keys may also come from ANTHROPIC_API_KEY / OPENAI_API_KEY,
    # which the official SDKs resolve themselves when these are empty. "openai" covers any
    # OpenAI-compatible endpoint (e.g. Nebius Token Factory via SOCRAT_OPENAI_BASE_URL).
    ai_provider: Literal["anthropic", "openai", "offline"] = "offline"
    ai_model: str = "claude-opus-5-5"
    ai_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    ai_server_fallbacks: bool = True
    anthropic_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("socrat_openai_api_key", "nebius_api_key", "openai_api_key"),
    )
    openai_api_key_file: str = ""
    openai_model: str = ""
    openai_base_url: str = ""
    ai_timeout_seconds: float = Field(default=45, ge=5, le=120)
    ai_daily_messages: int = Field(default=150, ge=1, le=5000)
    ai_reply_tokens: int = Field(default=1500, ge=200, le=8000)
    ai_tools: bool = True  # let the tutor look up the learner's data and the library
    # LLM cost guardrails. SOCRAT_AI_ENABLED=false is the kill switch: every model call stops
    # and the tutor answers with curated hints. Budgets are estimated from token counts and
    # the per-million-token prices below (set them to your provider's prices); 0 = no cap.
    ai_enabled: bool = True
    # Error reporting: always stored for /admin; also sent to Sentry/GlitchTip when set.
    sentry_dsn: str = ""
    release: str = ""
    ai_price_input_per_mtok: float = Field(default=3.0, ge=0, le=1000)
    ai_price_output_per_mtok: float = Field(default=15.0, ge=0, le=1000)
    ai_user_daily_budget_usd: float = Field(default=0.5, ge=0, le=1000)
    ai_daily_budget_usd: float = Field(default=25.0, ge=0, le=100_000)
    ai_monthly_budget_usd: float = Field(default=400.0, ge=0, le=1_000_000)
    ai_user_calls_per_minute: int = Field(default=12, ge=1, le=600)
    explainer_enabled: bool = True
    # Freemium plans (Razorpay Subscriptions). Off = no plan limits for anyone.
    billing_enabled: bool = False
    razorpay_key_id: str = Field(
        default="", validation_alias=AliasChoices("socrat_razorpay_key_id", "razorpay_key_id")
    )
    razorpay_key_secret: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("socrat_razorpay_key_secret", "razorpay_key_secret"),
    )
    razorpay_webhook_secret: SecretStr = SecretStr("")
    razorpay_key_secret_file: str = ""
    razorpay_webhook_secret_file: str = ""
    # Content system (Content Master Plan §8), on for adaptive learning. Safe on thin content:
    # unreviewed quiz families write no mastery evidence, and a pattern plan that breaks a
    # placement rule falls back to the classic composer. SOCRAT_*_ENABLED=false turns off.
    adaptive_quiz_enabled: bool = True
    pattern_planner_enabled: bool = True
    explainer_model: str = ""
    # 3D films need far more spatial reasoning than sketches: an optional stronger model (and
    # its prices, so usage is costed right) used only once a request is routed to 3D.
    explainer_3d_model: str = ""
    # 3D is still being tested: only admin accounts may request it (and Auto never picks it for
    # anyone else). Set false to open 3D to every learner.
    explainer_3d_admin_only: bool = True
    explainer_3d_price_input_per_mtok: float = Field(default=0, ge=0, le=1000)
    explainer_3d_price_output_per_mtok: float = Field(default=0, ge=0, le=1000)
    # Large models think before their first token; the tutor's short timeout is too tight.
    explainer_timeout_seconds: float = Field(default=180, ge=30, le=600)
    explainer_chat_template_kwargs: dict = Field(default_factory=dict)
    explainer_daily_messages: int = Field(default=20, ge=1, le=200)
    explainer_concurrent_limit: int = Field(default=4, ge=1, le=16)
    explainer_sandbox_origin: str = ""
    explainer_checker_url: str = ""
    explainer_checker_secret: SecretStr = SecretStr("")
    explainer_checker_secret_file: str = ""
    # Who may open /admin: OIDC subjects (or "issuer|subject"). Empty = nobody.
    admin_subjects: list[str] = Field(default_factory=list, max_length=50)
    # ...or verified Google emails. Only these addresses are ever stored (User.admin_email).
    admin_emails: list[str] = Field(
        default=["ramkrsnabhat@gmail.com", "sathishdutt0@gmail.com"], max_length=50
    )
    # Content review queue: drafts are YAML files on an authoring checkout; approval moves
    # them into the course folder for a commit. Empty means the repository defaults.
    content_drafts_dir: str = ""
    content_courses_dir: str = ""
    # Re-sync linked Codeforces profiles in the background (off in tests: no network).
    codeforces_autosync: bool = True
    # Course generation (docs/architecture/course-generation.md). Each agent role may use its
    # own provider, model, effort and prices, e.g. SOCRAT_GEN_ROLES='{"critic": {"provider":
    # "openai", "model": "...", "base_url": "..."}}'; unset keys fall back to SOCRAT_AI_*.
    gen_roles: dict[str, dict[str, str | float]] = Field(default_factory=dict)
    style_engine_enabled: bool = True  # learning styles; admin accounts only while testing
    # Learner-typed courses ("teach me X"): off until the owner turns it on.
    learning_requests_enabled: bool = False
    learning_requests_max_open: int = Field(default=3, ge=1, le=50)
    gen_visuals: bool = False  # Experience Designer adds typed visuals to generated lessons
    community_report_hold: int = Field(default=3, ge=1, le=100)  # distinct reporters hide a course
    community_max_shared: int = Field(default=5, ge=1, le=100)  # shared courses per learner
    learning_request_budget_usd: float = Field(default=3.0, gt=0, le=100)
    gen_runner: bool = True  # run queued generation jobs in the API process (off in tests)
    gen_timeout_seconds: float = Field(default=600, ge=30, le=3600)
    # Course Maintainer: scheduled link checks and repairs of released generated courses.
    maintainer_enabled: bool = False
    maintainer_batch: int = Field(default=200, ge=1, le=5000)  # links checked per pass
    maintainer_review_days: int = Field(default=365, ge=30, le=3650)
    gen_quarantine_reports: int = Field(default=3, ge=1, le=100)  # distinct learners
    ai_tool_rounds: int = Field(default=4, ge=1, le=8)

    # Local demo conveniences (seeded sample learners). Rejected outside development/test.
    demo_mode: bool = False

    # Beta community invite shown on the landing page and in the app ("" hides it).
    community_whatsapp_url: str = Field(
        default="", max_length=200, pattern=r"^(https://chat\.whatsapp\.com/[A-Za-z0-9]{10,40})?$"
    )

    # The signed-out "try a problem" tutor on the landing page. It shares the global AI
    # budgets and has its own daily cap and per-visitor limits.
    try_tutor_enabled: bool = True
    try_daily_budget_usd: float = Field(default=3.0, ge=0, le=10_000)
    try_messages_per_hour: int = Field(default=20, ge=1, le=500)

    # Email-and-password accounts. One-time codes are sent through Resend (resend.com) from a
    # verified domain; email_from looks like "Socrat <no-reply@example.com>".
    resend_api_key: SecretStr = SecretStr("")
    resend_api_key_file: str = ""
    email_from: str = Field(default="", max_length=200)

    @property
    def secure(self) -> bool:
        return self.environment in {"staging", "production"}

    @property
    def email_login_enabled(self) -> bool:
        # Local development writes codes to the API log instead of sending them.
        return bool(self.resend_api_key.get_secret_value() and self.email_from) or not self.secure

    @property
    def execution_enabled(self) -> bool:
        return bool(self.execution_profiles or self.browser_runtimes)

    @property
    def worker_execution_enabled(self) -> bool:
        return bool(self.execution_profiles)

    @model_validator(mode="after")
    def enforce_boundaries(self):
        if self.demo_mode and self.environment not in {"development", "test"}:
            raise ValueError("Demo mode is only accepted in development/test")
        if self.execution_backend in {"local_process", "demo_docker"} and self.secure:
            raise ValueError("The insecure local runner is only allowed in development/test")
        for name in ("execution_signing_secret", "execution_worker_secret"):
            setattr(
                self,
                name,
                _secret_from_file(name, getattr(self, name), getattr(self, f"{name}_file")),
            )
        if self.execution_profiles:
            if (
                len(self.execution_signing_secret.get_secret_value()) < 48
                or len(self.execution_worker_secret.get_secret_value()) < 48
                or self.execution_signing_secret == self.execution_worker_secret
            ):
                raise ValueError("Execution requires distinct strong signing and worker secrets")
            from socrat.execution.protocol import RuntimeProfile

            profiles = [RuntimeProfile.model_validate(x) for x in self.execution_profiles]
            if len({x.language for x in profiles}) != len(profiles) or len(
                {x.id for x in profiles}
            ) != len(profiles):
                raise ValueError("Execution requires unique runtime profiles")
        self.session_secret = _secret_from_file(
            "session_secret", self.session_secret, self.session_secret_file, LOCAL_SESSION_SECRET
        )
        self.oidc_client_secret = _secret_from_file(
            "oidc_client_secret", self.oidc_client_secret, self.oidc_client_secret_file
        )
        self.metrics_token = _secret_from_file(
            "metrics_token", self.metrics_token, self.metrics_token_file
        )
        self.openai_api_key = _secret_from_file(
            "openai_api_key", self.openai_api_key, self.openai_api_key_file
        )
        self.razorpay_key_secret = _secret_from_file(
            "razorpay_key_secret", self.razorpay_key_secret, self.razorpay_key_secret_file
        )
        self.razorpay_webhook_secret = _secret_from_file(
            "razorpay_webhook_secret",
            self.razorpay_webhook_secret,
            self.razorpay_webhook_secret_file,
        )
        self.explainer_checker_secret = _secret_from_file(
            "explainer_checker_secret",
            self.explainer_checker_secret,
            self.explainer_checker_secret_file,
        )
        self.resend_api_key = _secret_from_file(
            "resend_api_key", self.resend_api_key, self.resend_api_key_file
        )
        if self.environment == "test":
            self.codeforces_autosync = False
            self.gen_runner = False
        from socrat.coursegen.roles import check_roles

        check_roles(self.gen_roles)
        if self.ai_provider == "openai" and not self.openai_model:
            raise ValueError("The OpenAI provider requires SOCRAT_OPENAI_MODEL")
        if self.ai_provider == "anthropic" and not self.ai_model.startswith("claude-"):
            raise ValueError("The Anthropic provider requires a Claude model id")

        origin = urlparse(self.public_origin)
        if origin.scheme not in {"http", "https"} or not origin.netloc or origin.path:
            raise ValueError("public_origin must be an origin without a trailing slash")
        if not 300 <= self.session_ttl_seconds <= 90 * 86400:
            raise ValueError("Session lifetime must be between 5 minutes and 90 days")
        if self.dev_login_enabled and (
            self.secure or origin.hostname not in {"localhost", "127.0.0.1"}
        ):
            raise ValueError("Developer login is only allowed on local development/test origins")
        if self.secure:
            if not self.database_url_value.startswith("postgresql+psycopg://"):
                raise ValueError("Deployed environments require PostgreSQL")
            if (
                origin.scheme != "https"
                or len(self.session_secret.get_secret_value()) < 48
                or "local-development" in self.session_secret.get_secret_value()
            ):
                raise ValueError("Deployed environments require HTTPS and a unique session secret")
            if not (
                self.oidc_issuer.startswith("https://")
                and self.oidc_client_id
                and self.oidc_client_secret.get_secret_value()
            ):
                raise ValueError("Deployed environments require an OIDC provider")
            if len(self.metrics_token.get_secret_value()) < 32:
                raise ValueError("Deployed metrics require a private bearer token")
        return self
