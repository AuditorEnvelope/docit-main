from pydantic_settings import BaseSettings
from typing import Optional, List
from pydantic import AnyHttpUrl, field_validator, ConfigDict

class Settings(BaseSettings):
    # Application
    PROJECT_NAME: str = "Pustak AI"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development|staging|production
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str = "CHANGE_THIS_TO_A_SECURE_SECRET"
    JWT_SECRET: str = "CHANGE_THIS_TO_A_SECURE_SECRET"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000","https://lekhak-ai.onrender.com","https://cd17ff078a8e.ngrok-free.app", "http://localhost:8000", "https://www.docbook.site", "https://*.docbook.site", "https://docbook.site", "http://bajrangbalikijai.localhost:3000"]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # GitHub OAuth Configuration
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_OAUTH_CALLBACK_URL: str = "http://localhost:8000/api/v1/auth/callback"
    
    # GitHub App Configuration (Reader App)
    GITHUB_READER_APP_ID: str = "2072879"
    GITHUB_READER_PRIVATE_KEY: str = ""
    GITHUB_READER_INSTALLATION_ID: Optional[int] = None
    
    # GitHub App Configuration (Writer App)
    GITHUB_WRITER_APP_ID: str = "2229202"
    GITHUB_WRITER_PRIVATE_KEY: str = ""
    GITHUB_WRITER_INSTALLATION_ID: Optional[int] = None
    
    # GitHub Webhook
    GITHUB_WEBHOOK_SECRET: str = ""
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/pustak"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis (for caching and rate limiting)
    REDIS_URL: Optional[str] = None
    REDIS_ENABLED: bool = False
    
    # LLM Configuration
    LLM_PROVIDER: str = "openai"  # 'openai', 'anthropic', 'groq', or 'local'
    LLM_MODEL: str = "gpt-4"  # Default model to use
    LLM_MAX_TOKENS: int = 4000
    LLM_TEMPERATURE: float = 0.7
    LLM_TOP_P: float = 1.0
    
    # Provider-specific API keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GOOGLE_AI_API_KEY: str = ""
    
    # Rate Limiting
    RATE_LIMIT: int = 100  # requests per minute
    RATE_LIMIT_ENABLED: bool = True
    
    # Subscription Limits
    FREE_TIER_MAX_REPOS: int = 1
    PRO_TIER_MAX_REPOS: int = -1  # -1 = unlimited
    ENTERPRISE_TIER_MAX_REPOS: int = -1
    
    FREE_TIER_MAX_DOCS_PER_MONTH: int = 100
    PRO_TIER_MAX_DOCS_PER_MONTH: int = 1000
    ENTERPRISE_TIER_MAX_DOCS_PER_MONTH: int = -1  # unlimited
    
    # Stripe Configuration (for subscriptions)
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_ENABLED: bool = False
    
    # Documentation Generation
    AUTO_GENERATE_DOCS: bool = True
    DEFAULT_DOC_PERSONA: str = "developer"  # internal|developer
    
    # Docbook Configuration
    DOCBOOK_STAGING_BRANCH: str = "staging"
    DOCBOOK_MAIN_BRANCH: str = "main"
    DOCBOOK_AUTO_MERGE: bool = False
    
    # Background Processing
    ENABLE_EVENT_PROCESSOR: bool = True
    EVENT_PROCESSOR_INTERVAL_SECONDS: int = 5  # Match old codebase polling interval
    EVENT_POLL_INTERVAL: int = 5  # Seconds between polling for events (reduced from 60 for faster processing)
    MAX_EVENTS_PER_BATCH: int = 100
    EVENT_BATCH_SIZE: int = 100  # Number of events to process per batch
    EVENT_MAX_RETRIES: int = 3  # Maximum retries for failed events
    
    # Quality Checking
    ENABLE_QUALITY_CHECKS: bool = True
    MIN_QUALITY_SCORE: float = 70.0
    
    # Feature Flags
    ENABLE_HIERARCHICAL_DOCS: bool = True
    ENABLE_OVERLAY_SYSTEM: bool = True
    ENABLE_SMART_PROCESSOR: bool = True
    ENABLE_DOCBOOK_WORKFLOW: bool = True
    
    # Monitoring & Logging
    SENTRY_DSN: Optional[str] = None
    LOG_FORMAT: str = "json"  # json|text
    
    model_config = ConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"  # Ignore extra fields in .env
    )

settings = Settings()