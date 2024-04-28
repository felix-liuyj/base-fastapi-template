"""
Context from Code Snippet E:/Projects/Python/binary-owl-python-backend/app/api/__init__.py
"""
from functools import lru_cache

# from pydantic import BaseSettings
from pydantic.v1 import BaseSettings

__all__ = (
    'Settings',
    'get_settings',
)


class Settings(BaseSettings):
    APP_NAME: str
    APP_NO: str
    APP_ENV: str

    COOKIE_KEY: str
    DATA_REFRESH_SECONDS: int
    FRONTEND_DOMAIN: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_CLUSTER_NODE: str | None
    REDIS_USERNAME: str
    REDIS_PASSWORD: str

    MONGODB_USERNAME: str
    MONGODB_PASSWORD: str
    MONGODB_URI: str
    MONGODB_DB: str
    MONGODB_PORT: int
    MONGODB_AUTHENTICATION_SOURCE: str

    KAFKA_CLUSTER_BROKERS: str | None
    KAFKA_CLUSTER_TOPICS: str | None
    KAFKA_CLUSTER_CONSUMER_GROUP: str | None

    MAIL_HOST: str
    MAIL_PORT: int
    MAIL_USERNAME: str
    MAIL_PASSWORD: str

    JENKINS_HOST: str = None
    JENKINS_USERNAME: str = None
    JENKINS_PASSWORD: str = None
    JENKINS_TOKEN: str = None

    class Config:
        env_file = '.env'


@lru_cache()
def get_settings() -> Settings:
    return Settings()
