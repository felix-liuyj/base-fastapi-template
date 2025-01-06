import base64

import httpx
from fastapi import Request, HTTPException

from app.config import get_settings
from app.libs.sso import generate_un_auth_exception, SSOProviderEnum
from app.libs.sso.hktdc import parse_oauth_jwt, get_user_profile
from app.models.account import UserTitleEnum, UserStatusEnum, UserModel, UserProfile
from app.view_models import BaseViewModel

__all__ = (
    'UserLogoutViewModel',
    'AccountAuthCallbackViewModel',
    'UserInfoGetViewModel',
    'UserInfoListGetViewModel',
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
            api_response = await self.fetch_token_response_data(request_id)
            token_data = await parse_oauth_jwt(api_response.idToken)
            await self.redis.set(api_response.accessToken, token_data.email, ex=api_response.expiresIn)
            if not (user_profile := await get_user_profile(api_response.accessToken)):
                raise generate_un_auth_exception('Invalid token', SSOProviderEnum.HKTDC)
            if not await UserModel.find_one(UserModel.email == token_data.email):
                await UserModel.insert_one(UserModel(
                    ssoUid=user_profile.ssouid, email=user_profile.basicProfile.emailId,
                    name=user_profile.basicProfile.firstName, title=UserTitleEnum.SELLER,
                    username=f'{user_profile.basicProfile.firstName}{user_profile.basicProfile.lastName}'
                ))
            self.operating_successfully(api_response)
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Token exchange failed")

    async def fetch_token_response_data(self, request_id: str):
        # 请求令牌端点
        async with httpx.AsyncClient() as client:
            credentials = f'{get_settings().SSO_HKTDC_CLIENT_ID}:{get_settings().SSO_HKTDC_CLIENT_SECRET}'
            response = await client.post(
                f"{get_settings().SSO_HKTDC_BASE_URL}/uaa/oauth2/token",
                data={
                    "grant_type": "authorization_code",
                    "scope": 'openid /v2/shared-services/management/user-profile.readonly',
                    "code": self.code, "redirect_uri": str(get_settings().SSO_HKTDC_REDIRECT_URI),
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "x-request-id": f'CON-{request_id}',
                    'Authorization': f'Basic {base64.b64encode(credentials.encode("utf-8")).decode("utf-8")}'
                }
            )
        return response.raise_for_status().json()


class UserInfoGetViewModel(BaseViewModel):
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


class UserInfoListGetViewModel(BaseViewModel):
    def __init__(self, request: Request):
        super().__init__(request=request, access_title=[UserTitleEnum.BUYER, UserTitleEnum.SELLER])

    async def before(self):
        await super().before()
        self.operating_successfully([user.information async for user in UserModel.find(
            UserModel.affiliation == self.user_email
        )])


class ChangeUserStatusViewModel(BaseViewModel):
    def __init__(self, email: str, enable: bool, reason: str, request: Request):
        super().__init__(request=request, access_title=[UserTitleEnum.BUYER, UserTitleEnum.SELLER])
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
