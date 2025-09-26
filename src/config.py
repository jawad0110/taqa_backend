from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL : str
    JWT_SECRET : str
    JWT_ALGORITHM : str
    REDIS_URL : str = "rediss://:taqa0778@taqastore-sjz77-redis-master.taqastore-sjz77.svc.cluster.local:6379/0"
    REDIS_HOST : str
    REDIS_PORT :str
    
    MAIL_USERNAME : str
    MAIL_PASSWORD : str
    MAIL_FROM : str
    MAIL_PORT : int
    MAIL_SERVER : str
    MAIL_FROM_NAME : str
    MAIL_STARTTLS : bool = True
    MAIL_SSL_TLS : bool = False
    USE_CREDENTIALS : bool = True
    VALIDATE_CERTS : bool = True
    DOMAIN: Optional[str] = None
    FRONTEND_URL : str
    ACCESS_TOKEN_EXPIRY_DAYS : int = 7
    REFRESH_TOKEN_EXPIRY_DAYS : int = 30
    
    STATIC_URL: str = "/static"

    model_config = SettingsConfigDict(
        env_file = ".env",
        extra = "ignore"
    )


Config = Settings()

broker_url = Config.REDIS_URL
result_backend = Config.REDIS_URL
broker_connection_retry_on_startup = True
