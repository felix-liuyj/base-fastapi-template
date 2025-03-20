from pydantic import BaseModel, Field, AnyHttpUrl, EmailStr

__all__ = (
    'AccountLoginResponseData',
    'UserInfoListQueryResponseDataItem',
)

from app.models.account import UserTypeEnum


class AccountLoginResponseData(BaseModel):
    message: str = Field(
        ..., description='Login response message 登录响应消息', examples=['Login successfully']
    )
    token: str = Field(
        ..., description='Login response token 登录响应 token', examples=['eyJ0eXAiOi']
    )
    avatar: AnyHttpUrl = Field(
        ..., description='Account avatar url 头像地址', examples=['https://example.com/avatar.jpg']
    )
    email: str = Field(
        ..., description='Account email address 邮箱地址', examples=['example@example.com']
    )
    name: str = Field(
        ..., description='Account name 姓名', examples=['Example']
    )
    username: str = Field(
        ..., description='Account username 用户名', examples=['example']
    )
    affiliation: str | None = Field(
        ..., description='Account affiliation 所属单位', examples=['Example University']
    )


class UserInfoListQueryResponseDataItem(BaseModel):
    email: EmailStr = Field(..., description='Account email address 邮箱地址', examples=['example@example.com'])
    name: str = Field(..., description='Account name 姓名', examples=['Example'])
    username: str = Field(..., description='Account username 用户名', examples=['example'])
    userType: UserTypeEnum = Field(..., description='Account title 用户头衔', examples=[UserTypeEnum.SELLER])
