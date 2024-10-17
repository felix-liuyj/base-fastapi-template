from fastapi import Body
from pydantic import BaseModel

__all__ = (
    'LoginForm',
    'VerifyEmailForm',
)


class LoginForm(BaseModel):
    email: str = Body(..., embed=True)
    password: str = Body(..., embed=True)


class VerifyEmailForm(BaseModel):
    email: str = Body(..., embed=True)
    vCode: str = Body(..., embed=True)
