from typing import Optional

from fastapi import Body
from pydantic import BaseModel

__all__ = (
    'UpdateUserForm',
    'SetPasswordForm',
)


class UpdateUserForm(BaseModel):
    name: Optional[str] = Body('', embed=True, description='User name')
    username: Optional[str] = Body('', embed=True, description='User display name')
    disabled: Optional[bool] = Body(False, embed=True, description='Disabled, only can be used by admin')
    vCode: Optional[str] = Body(
        '', embed=True,
        description='Email verification code, only needed when change field include email'
    )


class SetPasswordForm(BaseModel):
    email: str = Body(..., embed=True)
    password: str = Body(..., embed=True)
    vCode: str = Body(..., embed=True)
