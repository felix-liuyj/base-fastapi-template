from enum import IntEnum, Enum
from typing import Annotated, Optional

from beanie import Indexed
from pydantic import Field, EmailStr, BaseModel
from pymongo import HASHED

from app.models import BaseDBModel

__all__ = (
    'UserTitleEnum',
    'SupportCertificateMIMEType',
    'CertificationItemType',
    'CertificationType',
    'UserModel',
)


class UserTitleEnum(IntEnum):
    ADMIN = 0
    ORGANIZATION = 1
    VOLUNTEER = 2


class SupportCertificateMIMEType(Enum):
    IMAGE_PNG = 'image/png'
    IMAGE_JPG = 'image/jpeg'
    IMAGE_JPEG = 'image/jpeg'
    APPLICATION_PDF = 'application/pdf'

    @classmethod
    def check_value_exists(cls, value: str) -> bool:
        for member in cls:
            if member.value == value:
                return cls(value)


class CertificationItemType(BaseModel):
    file_path: str
    file_type: SupportCertificateMIMEType


class CertificationType(BaseModel):
    identification_document: Optional[CertificationItemType] = None
    event_creation_licence_document: Optional[CertificationItemType] = None
    business_registration_certificate: Optional[CertificationItemType] = None

    @property
    def in_place(self):
        return all([
            self.identification_document, self.event_creation_licence_document, self.business_registration_certificate
        ])


class UserModel(BaseDBModel):
    # special string type that validates the email as a string
    email: Annotated[str, Indexed(EmailStr, unique=True)] = Field(
        ...,
        description='User email'
    )
    name: str = Field(
        ...,
        description='User display name (administrator name, organization name or volunteer name)'
    )
    username: str = Field(
        ...,
        description='User name'
    )
    password: str = Field(
        ...,
        description='User password'
    )
    title: UserTitleEnum = Field(
        default=UserTitleEnum.VOLUNTEER,
        description='User title'
    )
    affiliation: str = Field(
        default='',
        description='User affiliation, source from user email'
    )
    proven: bool = Field(
        default=False,
        description='Is User proved their title, organization or volunteer or admin'
    )
    certification: CertificationType | None = Field(
        default=None,
        description='Organization User title certification, only need when user is an organization'
    )

    class Settings:
        name = 'users'
        strict = False
        indexes = [
            [('_id', HASHED)],
        ]

    @property
    def information(self):
        result = {
            'email': self.email,
            'name': self.name,
            'username': self.username,
            'title': UserTitleEnum(self.title).name.title(),
            'affiliation': self.affiliation
        }
        if self.title == UserTitleEnum.ORGANIZATION:
            result.update(proven=self.proven)
        return result
