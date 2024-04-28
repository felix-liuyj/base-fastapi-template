import bcrypt
from fastapi import Request
from httpx import TimeoutException
from requests import ReadTimeout

from app.config import get_settings
from app.forms.common import *
from app.models.user import UserModel
from app.view_models import BaseViewModel

__all__ = (
    'RegisterViewModel',
    'GetUserInfoViewModel',
    'SendVerificationCodeViewModel',
    'VerifyEmailViewModel',
)


class RegisterViewModel(BaseViewModel):

    def __init__(self, form_data: RegisterAccountForm):
        super().__init__(need_auth=False)
        self.form_data = form_data

    async def before(self):
        try:
            await self.register()
        except TimeoutException as e:
            self.request_timeout(str(e))

    async def register(self):
        email = self.form_data.email.lower()
        user = await UserModel.find_one(UserModel.email == email)
        if user:
            self.forbidden('email already registered')
        await self.check_verification_code(email, self.form_data.vCode)
        salt = bcrypt.gensalt()
        user_info = await UserModel(
            email=email,
            firstName=self.form_data.first_name,
            lastName=self.form_data.last_name,
            companyName=self.form_data.company_name,
            address=self.form_data.address,
            emailVerified=False,
            isReseller=True,
            password=bcrypt.hashpw(self.form_data.password.encode('utf-8'), salt)
        ).insert()
        token = self.create_token(email, email, 'reseller')
        self.operating_successfully(dict(user_info) | {'token': token})


class GetUserInfoViewModel(BaseViewModel):
    def __init__(self, request: Request):
        super().__init__(request=request)

    async def before(self):
        try:
            extra_info = {}
            self.operating_successfully(self.user_instance.information | extra_info)
        except ReadTimeout as e:
            self.request_timeout(str(e))


class SendVerificationCodeViewModel(BaseViewModel):
    def __init__(self, form_data: ValidateEmailForm):
        super().__init__(need_auth=False)
        self.form_data = form_data
        self.sender = get_settings().MAIL_USERNAME

    async def before(self):
        try:
            await self.validate_email()
        except ReadTimeout as e:
            self.request_timeout(str(e))

    async def validate_email(self):
        token = self.generate_random_token(10)
        await self.send_email_with_verification_code(email=self.form_data.email, token=token)


class VerifyEmailViewModel(BaseViewModel):
    def __init__(self, form_data: VerifyEmailForm):
        super().__init__(need_auth=False)
        self.form_data = form_data
        self.sender = get_settings().MAIL_USERNAME

    async def before(self):
        try:
            await self.verify_email()
        except ReadTimeout as e:
            self.request_timeout(str(e))

    async def verify_email(self):
        user = await self.get_user_instance(self.form_data.email)
        if not user:
            self.not_found('user not found')
        await self.check_verification_code(self.form_data.email, self.form_data.vCode)
        await user.update_fields(emailVerified=True)
        self.operating_successfully('email verified')
