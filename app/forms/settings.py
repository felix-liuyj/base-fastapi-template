from fastapi import Body as _Body
from pydantic import BaseModel as _BaseModel

__all__ = (
    'SetPasswordForm',
)


class SetPasswordForm(_BaseModel):
    email: str = _Body(..., embed=True)
    password: str = _Body(..., embed=True)
    vCode: str = _Body(..., embed=True)
