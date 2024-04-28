from typing import Optional

from fastapi import Body as _Body
from pydantic import BaseModel as _BaseModel

__all__ = (
    'RegisterAccountForm',
    'LoginForm',
    'ValidateEmailForm',
    'VerifyEmailForm',
)


class RegisterAccountForm(_BaseModel):
    email: str = _Body(..., embed=True)
    password: str = _Body(..., embed=True)
    first_name: str = _Body(..., embed=True)
    last_name: str = _Body(..., embed=True)
    company_name: str = _Body(..., embed=True),
    address: Optional[str] = None
    vCode: str = _Body(..., embed=True)


class LoginForm(_BaseModel):
    email: str = _Body(..., embed=True)
    password: str = _Body(..., embed=True)


class ValidateEmailForm(_BaseModel):
    email: str = _Body(..., embed=True)


class VerifyEmailForm(_BaseModel):
    email: str = _Body(..., embed=True)
    vCode: str = _Body(..., embed=True)
