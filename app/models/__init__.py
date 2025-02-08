from datetime import datetime
from enum import Enum
from typing import Any

from beanie import Document, Update, after_event
from beanie.odm.operators.update.general import Set as _Set
from pydantic import Field

from app.config import get_settings
from app.libs.custom import encrypt, decrypt

__all__ = (
    'Set',
    'BaseDatabaseModel',
    'SupportImageMIMEType',
    'SupportDataMIMEType',
)


class Set(_Set):
    def __init__(self, expression):
        super().__init__(expression | {'updatedAt': datetime.now()})


class SupportDataMIMEType(Enum):
    TEXT_PLAIN = 'text/plain'
    TEXT_HTML = 'text/html'
    APPLICATION_JSON = 'application/json'

    @classmethod
    def check_value_exists(cls, value: str) -> 'SupportImageMIMEType':
        for member in cls:
            if member.value == value:
                return cls(value)


class SupportImageMIMEType(Enum):
    IMAGE_PNG = 'image/png'
    IMAGE_JPG = 'image/jpeg'
    IMAGE_JPEG = 'image/jpeg'
    IMAGE_SVG = 'image/svg+xml'

    @classmethod
    def check_value_exists(cls, value: str) -> 'SupportImageMIMEType':
        for member in cls:
            if member.value == value:
                return cls(value)


class BaseDatabaseModel(Document):
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

    def keys(self):
        return list(self.model_fields.keys())

    def __getitem__(self, item):
        return getattr(self, item) if item != 'id' else str(self.id)

    @property
    def sid(self) -> str:
        return str(self.id)

    @after_event(Update)
    async def refresh_update_at(self):
        self.updatedAt = datetime.now()

    async def update_fields(self, encrypt_fields: dict = None, **kwargs):
        if encrypt_fields and isinstance(encrypt_fields, dict):
            kwargs.update({key: encrypt(val, get_settings().ENCRYPT_KEY) for key, val in encrypt_fields.items()})

        kwargs.update(updatedAt=datetime.now())
        return await self.set(kwargs)

    async def get_encrypted_fields(self, encrypted_field: str) -> Any | None:
        if not getattr(self, encrypted_field):
            return None
        return decrypt(getattr(self, encrypted_field), get_settings().ENCRYPT_KEY)
