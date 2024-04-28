import abc
import random
import ssl
import string
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTPException, SMTP_SSL
from typing import Annotated

import jwt
from fastapi import Request, Depends
from jwt import ExpiredSignatureError, DecodeError

from app.config import get_settings, Settings
from app.libs.constants import ResponseStatusCodeEnum, get_response_message
from app.libs.controller.cache_controller import RedisCacheController
from app.libs.custom import cus_print, render_template
from app.models.user import UserModel

__all__ = (
    'ViewModelException',
    'ViewModelRequestException',
    'BaseViewModel',
)


class ViewModelException(Exception):
    pass


class ViewModelRequestException(ViewModelException):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class BaseViewModel:

    def __init__(self, request: Request = None, need_auth: bool = True):
        self.request: Request = request
        self.token = ''
        self.user_info = {}
        self.user_instance: UserModel = None
        self.need_auth = need_auth
        self.category = get_settings().APP_NO
        self.code = ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY.value
        self.message = get_response_message(ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY)
        self.data = ''
        self.sender = get_settings().MAIL_USERNAME

    def __enter__(self):
        try:
            self.__extract_token()
            self.before()
        except ViewModelRequestException:
            pass
        return self

    async def __aenter__(self):
        try:
            await self.__extract_token()
            await self.before()
        except ViewModelRequestException:
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.after()
        if exc_type:
            cus_print(f'{exc_type}: {exc_val}', )
        return True

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.after()
        if exc_type:
            cus_print(f'{exc_type}: {exc_val}', )
        return True

    async def __extract_token(self):
        if self.need_auth:
            self.token = self.request.headers.get('Authorization', '')
            await self.check_token()
            if not self.user_info:
                self.not_found('invalid token')

    @abc.abstractmethod
    async def before(self):
        pass

    async def after(self):
        pass

    @property
    def user_email(self):
        return self.user_info.get('email', '')

    @property
    def user_title(self):
        return self.user_info.get('title', '')

    @staticmethod
    def generate_random_token(length: int = 10):
        return ''.join(random.choice(string.digits + 'ABCDEF') for _ in range(length))

    @staticmethod
    def create_token(email, user_id: str, title: str):
        payload = {
            "userId": user_id,
            "email": email,
            "title": title,
            "exp": int(time.time()) + 60 * 60 * 24
        }
        cookie_key = get_settings().COOKIE_KEY
        token = jwt.encode(payload, cookie_key, algorithm='HS256')
        return token

    async def check_token(self) -> dict:
        if not self.token:
            self.unauthorized('Please pass the token in the authorization header to proceed')
        _, self.token = self.token.split(' ')
        self.user_info = self.verify_token()
        self.user_instance = await UserModel.find_one(UserModel.email == self.user_info.get('email'))
        if not self.user_instance:
            self.not_found('no user found')

    def verify_token(self) -> dict:
        try:
            jwt_verify_result = jwt.decode(self.token, get_settings().COOKIE_KEY, algorithms=['HS256']) or {}
            if not jwt_verify_result:
                self.unauthorized('please pass the token in the authorization header to proceed')
            if not jwt_verify_result.get('userId'):
                self.unauthorized('invalid token')
            return jwt_verify_result
        except ExpiredSignatureError:
            self.unauthorized('token expired. Please login again to continue')
        except DecodeError:
            self.unauthorized('invalid token')

    async def get_user_instance(self, email) -> UserModel:
        if user := await UserModel.find_one(UserModel.email == email):
            pass
        else:
            self.not_found('email not registered')
        return user

    def operating_successfully(self, data: str | dict | list):
        self.code = ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY.value
        self.message = get_response_message(ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY)
        self.data = data
        raise ViewModelRequestException(message=data)

    def empty_content(self, data: str | dict | list):
        self.code = ResponseStatusCodeEnum.EMPTY_CONTENT.value
        self.message = get_response_message(ResponseStatusCodeEnum.EMPTY_CONTENT)
        self.data = data
        raise ViewModelRequestException(message=data)

    def nothing_changed(self, data: str | dict | list):
        self.code = ResponseStatusCodeEnum.NOTHING_CHANGED.value
        self.message = get_response_message(ResponseStatusCodeEnum.NOTHING_CHANGED)
        self.data = data
        raise ViewModelRequestException(message=data)

    def operating_failed(self, msg: str):
        self.code = ResponseStatusCodeEnum.OPERATING_FAILED.value
        self.message = get_response_message(ResponseStatusCodeEnum.OPERATING_FAILED)
        self.data = msg
        raise ViewModelRequestException(message=msg)

    def unauthorized(self, msg: str):
        self.code = ResponseStatusCodeEnum.UNAUTHORIZED.value
        self.message = get_response_message(ResponseStatusCodeEnum.UNAUTHORIZED)
        self.data = msg
        raise ViewModelRequestException(message=msg)

    def forbidden(self, msg: str):
        self.code = ResponseStatusCodeEnum.FORBIDDEN.value
        self.message = get_response_message(ResponseStatusCodeEnum.FORBIDDEN)
        self.data = msg
        raise ViewModelRequestException(message=msg)

    def not_found(self, msg: str):
        self.code = ResponseStatusCodeEnum.NOT_FOUND.value
        self.message = get_response_message(ResponseStatusCodeEnum.NOT_FOUND)
        self.data = msg
        raise ViewModelRequestException(message=msg)

    def illegal_parameters(self, msg: str):
        self.code = ResponseStatusCodeEnum.ILLEGAL_PARAMETERS.value
        self.message = get_response_message(ResponseStatusCodeEnum.ILLEGAL_PARAMETERS)
        self.data = msg
        raise ViewModelRequestException(message=msg)

    def request_timeout(self, msg: str):
        self.code = ResponseStatusCodeEnum.REQUEST_TIMEOUT.value
        self.message = get_response_message(ResponseStatusCodeEnum.REQUEST_TIMEOUT)
        self.data = msg
        raise ViewModelRequestException(message=msg)

    def system_error(self, msg: str):
        self.code = ResponseStatusCodeEnum.SYSTEM_ERROR.value
        self.message = get_response_message(ResponseStatusCodeEnum.SYSTEM_ERROR)
        self.data = msg
        raise ViewModelRequestException(message=msg)

    def send_email(
            self, sender: str, receiver: str, body: str, subject: str = 'subject',
            settings: Annotated[Settings, Depends(get_settings)] = None
    ) -> bool:
        try:
            message = MIMEMultipart("alternative")
            message['From'] = sender
            message['To'] = receiver
            message['Subject'] = subject

            part = MIMEText(body, "html")
            message.attach(part)

            context = ssl.create_default_context()
            context.set_ciphers('DEFAULT')

            with SMTP_SSL(settings.MAIL_HOST, settings.MAIL_PORT, context=context) as server:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                server.sendmail(settings.MAIL_USERNAME, receiver, message.as_string())
            return True
        except SMTPException:
            return False
        except Exception as ex:
            self.system_error(f'system error for sending email: {str(ex)}, please contact the system administrator')

    async def send_email_with_verification_code(self, token: str, email: str):
        email_body = render_template('email/verification-code-template.html', {
            'email': email, 'code': token
        })
        if self.send_email(self.sender, email, email_body, 'Verification Code For Binary Owl'):
            async with RedisCacheController() as redis_cache:
                await redis_cache.set(f'{email}-verification-code', token, 60 * 10)
            self.operating_successfully('email sent successfully')
        else:
            self.operating_failed('email sending failed')

    async def check_verification_code(self, email: str, token: str) -> bool:
        async with RedisCacheController() as redis_cache:
            if await redis_cache.check_email_v_code(email, token):
                await redis_cache.clear(key=f'{email}-verification-code')
                return True
            self.illegal_parameters('invalid verification code')

    @staticmethod
    def keys():
        return 'category', 'code', 'message', 'data'

    def __getitem__(self, item):
        return getattr(self, item)
