import bcrypt
from fastapi import Request
from requests import ReadTimeout

from app.forms.common import *
from app.view_models import BaseViewModel

__all__ = (
    'UserLoginViewModel',
    'UserLogoutViewModel',
)


class UserLoginViewModel(BaseViewModel):
    def __init__(self, form_data: LoginForm):
        super().__init__(need_auth=False)
        self.form_data = form_data

    async def before(self):
        try:
            await self.login()
        except ReadTimeout as e:
            self.request_timeout(str(e))

    async def login(self):
        email = self.form_data.email.lower()
        user = await self.get_user_instance(email)
        if user.password is None:
            self.operating_failed('password not set')
        if not bcrypt.checkpw(self.form_data.password.encode('utf-8'), user.password.encode('utf-8')):
            self.operating_failed('password not matched')
        extra_info = {}
        self.operating_successfully(
            {
                'message': 'login successfully',
                'token': self.create_token(user.email, user.email, user.typeOfUser)
            } | user.information | extra_info
        )


class UserLogoutViewModel(BaseViewModel):

    def __init__(self, request: Request):
        super().__init__(request=request)

    async def before(self):
        try:
            self.logout()
        except ReadTimeout as e:
            self.request_timeout(str(e))

    def logout(self):
        self.operating_successfully('logged out successfully')
