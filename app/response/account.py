from pydantic import BaseModel, Field, AnyHttpUrl, EmailStr

__all__ = (
    'AccountLoginResponseData',
    'UserInfoListQueryResponseDataItem',
)

from app.models.account import UserTypeEnum


class AccountLoginResponseData(BaseModel):
    message: str = Field(..., description='Login response message 登录响应消息')
    token: str = Field(..., description='Login response token 登录响应 token')
    avatar: AnyHttpUrl = Field(..., description='Account avatar url 头像地址')
    email: str = Field(..., description='Account email address 邮箱地址')
    name: str = Field(..., description='Account name 姓名')
    username: str = Field(..., description='Account username 用户名')
    affiliation: str | None = Field(..., description='Account affiliation 所属单位')

    class Config:
        schema_extra = {
            'examples': [
                {
                    'message': 'Login successfully',
                    'token': 'eyJ0eXAiOi',
                    'avatar': 'https://example.com/avatar.jpg',
                    'email': 'example@example.com',
                    'name': 'Example',
                    'username': 'example',
                    'affiliation': 'Example University'
                }
            ]
        }


class UserInfoListQueryResponseDataItem(BaseModel):
    email: EmailStr = Field(..., description='Account email address 邮箱地址')
    name: str = Field(..., description='Account name 姓名')
    username: str = Field(..., description='Account username 用户名')
    userType: UserTypeEnum = Field(..., description='Account title 用户头衔')

    class Config:
        schema_extra = {
            'examples': [
                {
                    'email': 'example@example.com',
                    'name': 'Example',
                    'username': 'example',
                    'userType': UserTypeEnum.SELLER
                }
            ]
        }
