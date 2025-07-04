"""
Context from Code Snippet E:/Projects/Python/binary-owl-python-backend/app/api/__init__.py
"""
import pathlib
from functools import lru_cache

from pydantic import AnyHttpUrl
from pydantic.v1 import BaseSettings

__all__ = (
    'Settings',
    'get_settings',
)


class Settings(BaseSettings):
    APP_NAME: str
    APP_NO: str
    APP_ENV: str

    ENCRYPT_KEY: str | None
    FRONTEND_DOMAIN: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_CLUSTER_NODE: str | None
    REDIS_USERNAME: str = 'default'
    REDIS_PASSWORD: str

    MONGODB_USERNAME: str
    MONGODB_PASSWORD: str
    MONGODB_URI: str
    MONGODB_DB: str
    MONGODB_PORT: int
    MONGODB_AUTHENTICATION_SOURCE: str

    MYSQL_USERNAME: str
    MYSQL_PASSWORD: str
    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_DATABASE: str

    KAFKA_CLUSTER_BROKERS: str | None
    KAFKA_CLUSTER_TOPICS: str | None
    KAFKA_CLUSTER_CONSUMER_GROUP: str | None
    KAFKA_CLUSTER_SASL_USERNAME: str | None
    KAFKA_CLUSTER_SASL_PASSWORD: str | None

    SMTP_HOST: str
    SMTP_USERNAME: str
    SMTP_API_USER: str
    SMTP_PASSWORD: str
    SMTP_PORT: int

    ALI_OSS_ACCESS_KEY: str | None = None
    ALI_OSS_ACCESS_SECRET: str | None = None
    ALI_OSS_REGION: str | None = None
    ALI_OSS_BUCKET_NAME: str | None = None

    AZURE_BLOB_ACCOUNT_NAME: str | None = None
    AZURE_BLOB_ACCESS_TOKEN: str | None = None
    AZURE_BLOB_CONTAINER_NAME: str | None = None

    SSO_AZURE_CLIENT_ID: str
    SSO_AZURE_CLIENT_SECRET: str
    SSO_AZURE_CALLBACK_PATH: str
    SSO_AZURE_REDIRECT_URI: AnyHttpUrl
    SSO_AZURE_BASE_URL: AnyHttpUrl

    class Config:
        env_file = f'{pathlib.Path(__file__).resolve().parent.parent.parent}/.env'


@lru_cache()
def get_settings() -> Settings:
    return Settings()
