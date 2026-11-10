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
    # Compatible endpoints only (ignored for api.openai.com): sent with every call, e.g.
    # {"thinking": false} for DeepSeek, so a model does not reason for seconds before answering.
    openai_chat_template_kwargs: dict = Field(default_factory=dict)
    # Ask OpenAI-compatible endpoints for a JSON object (response_format) on course-generation
    # calls, so a long outline cannot come back with a stray comma. Off for endpoints without it.
    openai_json_mode: bool = False
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
    # Sketches as declarative data played by host code (explainer/sketch.py) instead of a
    # model-written HTML page with scripts. Off until the owner switches it on.
    explainer_sketch_declarative: bool = False
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
    # "chat_template_kwargs" (an object) overrides SOCRAT_OPENAI_CHAT_TEMPLATE_KWARGS per role.
    gen_roles: dict[str, dict[str, str | float | dict]] = Field(default_factory=dict)
    # Model tiers (coursegen/roles.ROLE_TIER): "strong" for the plan, the checks and rewrites
    # of failed lessons; "fast" for reading and sorting; everything else stays on SOCRAT_AI_*.
    # Same keys as SOCRAT_GEN_ROLES, e.g. SOCRAT_GEN_TIERS='{"strong": {"model": "...",
    # "price_input_per_mtok": 3, "price_output_per_mtok": 15}, "fast": {"model": "..."}}'.
    # Empty: every role runs on the default model, as before. A role's own entry in
    # SOCRAT_GEN_ROLES wins over its tier.
    gen_tiers: dict[str, dict[str, str | float | dict]] = Field(default_factory=dict)
    # What one released lesson should cost at most. Nothing is stopped by it: courses above
    # it are marked in the owner's cost report, so a dear course is seen, not discovered.
    gen_lesson_cost_target_usd: float = Field(default=0.10, ge=0, le=100)
    # Write-check-revise rounds per lesson package. Revisions are targeted edits, so a round
    # costs little; subjects the model knows less well (a live Kannada course) need more.
    gen_package_rounds: int = Field(default=3, ge=1, le=8)
    # What blocks a lesson is a defect: a deterministic gate that fails, a fact-check claim marked
    # `incorrect`, or a review that could not be read. The reviewer's 1 to 5 rubric scores are a
    # signal, noisy with a cheap model, so a score below target (5 for correctness, 4 for the
    # rest) is a visible warning. Only a score below this floor blocks, as a sign the lesson is
    # seriously weak. Raise it as stronger models arrive.
    gen_score_floor: int = Field(default=3, ge=2, le=5)
    style_engine_enabled: bool = True  # learning styles; admin accounts only while testing
    # Learner-typed courses ("teach me X"): off until the owner turns it on.
    learning_requests_enabled: bool = False
    learning_requests_max_open: int = Field(default=3, ge=1, le=50)
    # Per learner, per process (see limits.py); 0 turns a limit off.
    simulate_per_minute: int = Field(default=60, ge=0, le=10_000)
    diagnostic_per_hour: int = Field(default=10, ge=0, le=1000)
    gen_visuals: bool = False  # Experience Designer adds typed visuals to generated lessons
    # Quiz and atom writers mark the right option in the item instead of giving its index
    # (coursegen/keyed.py). Replies in either form are always accepted; this changes the ask.
    gen_marked_answers: bool = False
    # Learner courses end every module with a planned "Apply" lesson that uses the module's
    # ideas together in a new situation (coursegen/applied.py).
    gen_applied_lessons: bool = False
    # Lessons are written as pages sized for the learner (style/pages.py); the page gate
    # replaces the character floor and ceiling.
    gen_lesson_pages: bool = False
    # Search providers the researcher must choose sources from (coursegen.search.PROVIDERS),
    # e.g. ["wikipedia", "wikibooks", "arxiv", "open-library"]. Empty: the model names sources from memory
    # and only the link check guards them.
    research_providers: list[str] = Field(default_factory=list)
    # "web" in research_providers searches articles and the wider web with the Brave Search
    # API; it adds nothing without this key. "openalex" works without a key on a small shared
    # allowance and uses this one when set.
    web_search_api_key: SecretStr = SecretStr("")
    openalex_api_key: SecretStr = SecretStr("")
    # Read the pages the researcher picked (public https only, robots.txt honoured) and give
    # their text to the author, so a lesson is written from the source and not from a
    # two-line search snippet. Only used when research_providers is set.
    research_read_pages: bool = True
    # "youtube" in research_providers searches videos and playlists with the YouTube Data API
    # (a free Google Cloud key; about 100 lessons a day on the free quota).
    youtube_api_key: SecretStr = SecretStr("")
    # Read the public captions of the videos the researcher picks and give them to the author
    # as source text. There is no official API for this (youtube-transcript-api reads the
    # watch page), so it is off until the owner turns it on.
    youtube_transcripts: bool = False
    # Lite mode on slow or metered connections: heavy web parts load only when asked for.
    lite_mode_enabled: bool = False
    community_report_hold: int = Field(default=3, ge=1, le=100)  # distinct reporters hide a course
    community_max_shared: int = Field(default=5, ge=1, le=100)  # shared courses per learner
    learning_request_budget_usd: float = Field(default=3.0, gt=0, le=100)
    gen_runner: bool = True  # run queued generation jobs in the API process (off in tests)
    # Generation jobs the API process runs at once. With 1 a course's first lessons are written
    # one after another; with 3-4 the first lesson is not kept waiting behind the others.
    gen_runner_concurrency: int = Field(default=1, ge=1, le=16)
    # Admin-published courses: write the first slice at once (learner courses always do).
    gen_initial_on_publish: bool = False
    # A learner's first lesson starts when their plan is saved, not when they press Start.
    gen_early_first_lesson: bool = True
    # A learner's first lesson takes the search's best-ranked sources as they are, without the
    # researcher's model call: one step fewer before the author starts. Links are still checked.
    gen_fast_first_lesson: bool = False
    # The learner may read their first lesson's draft once it has passed the lesson gates,
    # labelled as still being checked, while its quiz is written and the fact check and review
    # run. Read-only: nothing is marked done from a draft. Never for a course with safety
    # notes or a learner under 13. Off until the owner decides (spec, owner decisions).
    gen_first_lesson_preview: bool = False
    # Split deployment: API with SOCRAT_GEN_RUNNER=false, worker with SOCRAT_WORKER_RUNS_GENERATION=true.
    # Claims are atomic, so running both is safe too (a job is taken by exactly one process).
    worker_runs_generation: bool = False
    worker_generation_concurrency: int = Field(default=1, ge=1, le=16)
    # The worker touches this file every loop; `python -m socrat.worker --check` fails when stale.
    worker_heartbeat_file: str = ""
    gen_timeout_seconds: float = Field(default=600, ge=30, le=3600)
    # Critic reviews per outline job. Each "revise" costs a full new outline round; with 1, the
    # outline revised after the first review is kept without a second review. 0: the critic
    # still reviews (logged for the owner and the learner) but never asks for a rewrite, so the
    # blueprint is ready after one round.
    gen_outline_reviews: int = Field(default=3, ge=0, le=3)
    # Course Maintainer: scheduled link checks and repairs of released generated courses.
    maintainer_enabled: bool = False
    maintainer_batch: int = Field(default=200, ge=1, le=5000)  # links checked per pass
    maintainer_review_days: int = Field(default=365, ge=30, le=3650)
    maintainer_replacements: int = Field(default=3, ge=0, le=50)  # researcher calls per pass
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
        from socrat.coursegen.roles import check_roles, check_tiers

        check_roles(self.gen_roles)
        check_tiers(self.gen_tiers)
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
