import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgres://user:password@db:5432/notification_db")
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://user:password@rabbitmq:5672/")
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", 3))

    class Config:
        env_file = ".env"

settings = Settings()
