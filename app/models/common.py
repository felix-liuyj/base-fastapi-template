from typing import Annotated, Optional

from beanie import Indexed
from pydantic import BaseModel
from pydantic import Field, EmailStr
from pymongo import HASHED

from app.config import get_settings
from app.libs.ctrl.db.mongodb import BaseDatabaseModel
from app.libs.custom import decrypt
from app.models import SupportImageMIMEType

__all__ = (
    'UserModel',
    'ImageFileType',
)


class ImageFileType(BaseModel):
    file_path: str
    file_type: SupportImageMIMEType


class UserModel(BaseDatabaseModel):
    # special string type that validates the email as a string
    email: Annotated[EmailStr, Indexed(EmailStr, unique=True)] = Field(..., description='User email')
    name: str = Field(..., description='User name (administrator name, organization name or volunteer name)')
    username: str = Field(..., description='User display name')
    avatar: ImageFileType = Field(
        default=ImageFileType(file_path='account-avatar/default.png', file_type=SupportImageMIMEType.IMAGE_PNG),
        description='User avatar oss file info'
    )
    password: Optional[str] = Field('', description='User password')
    affiliation: Optional[str] = Field(None, description='User affiliation, source from user email or team id')

    class Settings:
        name = 'users'
        strict = False
        indexes = [
            [('_id', HASHED)],
        ]

    def check_password(self, password: str) -> bool:
        if not password:
            return False
        print(f'Encrypt Key: {get_settings().ENCRYPT_KEY}')
        return decrypt(self.password, get_settings().ENCRYPT_KEY) == password

    @property
    def information(self):
        result = {
            'email': self.email,
            'name': self.name,
            'username': self.username,
        }
        return result
