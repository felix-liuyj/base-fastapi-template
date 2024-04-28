from typing import Annotated

from beanie import Indexed
from pydantic import Field, EmailStr
from pymongo import HASHED

from app.models import BaseDBModel

__all__ = (
    'UserModel',
)


class UserModel(BaseDBModel):
    # special string type that validates the email as a string
    email: Annotated[str, Indexed(EmailStr, unique=True)] = Field(...)
    firstName: str = Field(...)
    lastName: str = Field(...)
    password: str = Field(...)

    class Settings:
        name = 'users'
        strict = False
        indexes = [
            [('_id', HASHED)],
        ]
