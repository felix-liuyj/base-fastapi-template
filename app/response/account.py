from pydantic import BaseModel, Field, AnyHttpUrl

__all__ = (
    'AccountLoginResponseData',
)


class AccountLoginResponseData(BaseModel):
    message: str = Field(..., description='Login response message')
    token: str = Field(..., description='Login response token')
    avatar: AnyHttpUrl = Field(..., description='Account avatar url')
    email: str = Field(..., description='Account email')
    name: str = Field(..., description='Account name')
    username: str = Field(..., description='Account username')
    affiliation: str | None = Field(..., description='Account affiliation')
