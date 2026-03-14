from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BOOTSTRAP_ADMIN_TOKEN: str | None = None
    AUTH_RATE_LIMIT_MAX_ATTEMPTS: int = 10
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_MAX_PER_IP: int = 120
    RATE_LIMIT_MAX_PER_USER: int = 300
    PRODUCTS_MAX_PAGE_SIZE: int = 100
    ANALYTICS_MAX_RANGE_DAYS: int = 93
    REDIS_URL: str
    TTL_PRODUCTS_LIST: int =  120
    TTL_CATEGORIES: int = 600
    TTL_USER: int = 60
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    REDIS_PASSWORD: str

    class Config:
        env_file = ".env"

settings = Settings()
