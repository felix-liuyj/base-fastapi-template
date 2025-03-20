import httpx
from fastapi import Request, HTTPException

from app.libs.sso import generate_un_auth_exception, SSOProviderEnum
from app.models.account import UserTypeEnum, UserStatusEnum, UserModel, UserProfile
from app.view_models import BaseViewModel

__all__ = (
    'UserLogoutViewModel',
    'AccountAuthCallbackViewModel',
    'UserInfoQueryViewModel',
    'UserInfoListQueryViewModel',
    'ChangeUserStatusViewModel',
    'VerificationCodeSendViewModel',
)


class UserLogoutViewModel(BaseViewModel):

    def __init__(self, request: Request, user_profile: UserProfile = None):
        super().__init__(request=request, user_profile=user_profile)

    async def before(self):
        await super().before()
        self.logout()

    def logout(self):
        self.operating_successfully('logged out successfully')


class AccountAuthCallbackViewModel(BaseViewModel):

    def __init__(self, code: str, state: str):
        super().__init__(None)
        self.code = code
        self.state = state

    async def before(self):
        if not (request_id := await self.redis.get(self.state)):
            raise generate_un_auth_exception('Invalid state', SSOProviderEnum.HKTDC)

        await self.check_code(request_id)

    async def check_code(self, request_id: str):
        try:
            self.operating_successfully(True)
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Token exchange failed")


class UserInfoQueryViewModel(BaseViewModel):
    def __init__(self, request: Request, user_profile: UserProfile):
        super().__init__(request=request, user_profile=user_profile)
        self.user_data = user_profile

    async def before(self):
        await super().before()
        # TODO: 用户模型
        self.operating_successfully(
            self.user_data.model_dump()
            # self.user_instance.information | {'avatar': await self.gen_access_url(self.user_instance.avatar.file_path)}
        )


class UserInfoListQueryViewModel(BaseViewModel):
    def __init__(self, request: Request):
        super().__init__(request=request, access_title=[UserTypeEnum.BUYER, UserTypeEnum.SELLER])

    async def before(self):
        await super().before()
        self.operating_successfully([user.information async for user in UserModel.find(
            UserModel.affiliation == self.user_email
        )])


class ChangeUserStatusViewModel(BaseViewModel):
    def __init__(self, email: str, enable: bool, reason: str, request: Request):
        super().__init__(request=request, access_title=[UserTypeEnum.BUYER, UserTypeEnum.SELLER])
        self.email = email
        self.enable = enable
        self.reason = reason

    async def before(self):
        await super().before()
        if not (user := await UserModel.find_one(
                UserModel.email == self.email, UserModel.affiliation == self.user_instance.sid
        )):
            self.not_found('user not found')
        if user.status == UserStatusEnum.NEEDS_APPROVAL:
            self.forbidden('user needs approval first')
        if user.status == UserStatusEnum.ACTIVE if self.enable else UserStatusEnum.DISABLED:
            self.forbidden(f'user already in {"enabled" if self.enable else "disabled"}')
        await user.update_fields(status=UserStatusEnum.ACTIVE if self.enable else UserStatusEnum.DISABLED)
        self.operating_successfully(
            f'status of user {self.email} changed to {"Enabled" if self.enable else "Disabled"} successfully'
        )


class VerificationCodeSendViewModel(BaseViewModel):
    def __init__(self, email: str):
        super().__init__()
        self.email = email

    async def before(self):
        await super().before()
        await self.send_email_v_code()

    async def send_email_v_code(self):
        self.operating_failed('failed to send verification code')
