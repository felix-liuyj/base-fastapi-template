"""
Context from Code Snippet E:/Projects/Python/binary-owl-python-backend/app/api/__init__.py
"""
import pathlib
from functools import lru_cache

from pydantic import HttpUrl
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
    INTEGRATION_API_KEY: str
    FAKER_DATA_TARGET_NUMBER: int

    COOKIE_KEY: str
    ENCRYPT_KEY: str | None
    DATA_REFRESH_SECONDS: int
    FRONTEND_DOMAIN: str
    PAYMENT_GATEWAY_DOMAIN: str
    ISA_DOMAIN: str

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
    KAFKA_CLUSTER_SASL_USERNAME: str | None
    KAFKA_CLUSTER_SASL_PASSWORD: str | None

    REDIS_CONNECTION_STRING: str

    COSMOS_DB_NAME: str
    COSMOS_DB_CONNECTION_STRING: str

    SMTP_API_HOST: str
    SMTP_USERNAME: str
    SMTP_API_USER: str
    SMTP_API_KEY: str
    SMTP_API_PORT: int

    ALI_OSS_ACCESS_KEY: str
    ALI_OSS_ACCESS_SECRET: str
    ALI_OSS_REGION: str
    ALI_OSS_BUCKET_NAME: str

    AZURE_BLOB_ACCOUNT_NAME: str
    AZURE_BLOB_ACCESS_TOKEN: str
    AZURE_BLOB_CONTAINER_NAME: str

    SSO_AZURE_CLIENT_ID: str
    SSO_AZURE_CLIENT_SECRET: str
    SSO_AZURE_CALLBACK_PATH: str
    SSO_AZURE_REDIRECT_URI: HttpUrl
    SSO_AZURE_BASE_URL: HttpUrlπ

    class Config:
        env_file = f'{pathlib.Path(__file__).resolve().parent.parent.parent}/.env'


@lru_cache()
def get_settings() -> Settings:
    return Settings()
