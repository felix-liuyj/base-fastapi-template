import abc
import json
import random
import string
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import jwt
from dateutil.relativedelta import relativedelta
from faker.proxy import Faker
from fastapi import Request, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jenkins import TimeoutException
from jwt import ExpiredSignatureError, DecodeError
from pydantic import EmailStr, BaseModel
from starlette import status

from app.config import get_settings
from app.libs.cloud_provider import AliCloudOssBucketController
from app.libs.constants import ResponseStatusCodeEnum, get_response_message
from app.libs.custom import cus_print, render_template
from app.libs.integration_api_controller import IntegrationApiCommonController
from app.libs.mlpg_api_controller import MLPGTransactionApiController, PaymentGatewayEnum
from app.models.account import UserTitleEnum, ImageFileType
from app.models.account.admin import AdminConfigurationModel
from app.models.common import UserModel
from app.models.account.organization import OrganizationConfigurationModel
from app.response import ResponseModel

__all__ = (
    'get_current_user_config',
    'ViewModelException',
    'ViewModelRequestException',
    'BaseViewModel',
    'BaseOssViewModel',
    'BaseUserCertificateOssViewModel',
    'BaseEventOssViewModel',
    'BasePaymentProductOssViewModel',
    'BaseAccountAvatarOssViewModel',
    'BasePaymentViewModel',
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class TokenData(BaseModel):
    userId: str
    email: EmailStr
    title: str
    exp: int


def generate_un_auth_exception(msg: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=msg, headers={"Authenticate": "Bearer"}
    )


def verify_token(token: str) -> TokenData:
    try:
        jwt_verify_result = jwt.decode(token, get_settings().COOKIE_KEY, algorithms=['HS256']) or {}
        token_data = TokenData(**jwt_verify_result)
        if not jwt_verify_result:
            raise generate_un_auth_exception('please pass the token in the authorization header to proceed')
        if not jwt_verify_result.get('userId'):
            raise generate_un_auth_exception('invalid token')
        return token_data
    except ExpiredSignatureError:
        raise generate_un_auth_exception('token expired. Please login again to continue')
    except DecodeError:
        raise generate_un_auth_exception('invalid token')


# Dependency to extract token and load user config
async def get_current_user_config(token: str = Depends(oauth2_scheme)) -> UserModel:
    token_data = verify_token(token)
    if not (user_instance := await UserModel.find_one(UserModel.email == token_data.email)):
        raise generate_un_auth_exception('no user found')
    if token_data.access_title and token_data.user_instance.title not in token_data.access_title:
        raise generate_un_auth_exception('operation not allowed')
    return user_instance


class ViewModelException(Exception):
    pass


class ViewModelRequestException(ViewModelException):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class BaseViewModel:

    def __init__(self, request: Request = None, need_auth: bool = True, access_title: list[UserTitleEnum] = None):
        self.request: Request = request
        self.token = ''
        self.user_info = {}
        self.user_instance: UserModel = None
        self.user_configuration: AdminConfigurationModel | OrganizationConfigurationModel = None
        self.need_auth = need_auth
        self.access_title = access_title
        self.faker = Faker()
        self.category = get_settings().APP_NO
        self.code = ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY.value
        self.message = get_response_message(ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY)
        self.data = None

    def __enter__(self):
        try:
            self.__extract_token()
            self.before()
        except ViewModelRequestException:
            pass
        return ResponseModel(
            category=self.category,
            code=self.code,
            message=self.message,
            data=self.data
        )
        # return self

    async def __aenter__(self):
        try:
            await self.__extract_token()
            await self.before()
        except TimeoutException as e:
            self.request_timeout(str(e))
        except ViewModelRequestException:
            pass
        return ResponseModel(
            category=self.category,
            code=self.code,
            message=self.message,
            data=self.data
        )

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
            if not (header := self.request.headers):
                self.unauthorized('please pass the token in the authorization header to proceed')
            self.token = header.get('Authorization', '')
            await self.check_token()
            if not self.user_instance:
                self.not_found('invalid token')
            if self.access_title and self.user_instance.title not in self.access_title:
                self.forbidden('operation not allowed')
            match self.user_instance.title:
                case UserTitleEnum.ADMIN:
                    self.user_configuration = await AdminConfigurationModel.find_one(
                        AdminConfigurationModel.affiliation == self.user_email
                    )
                case UserTitleEnum.ORGANIZATION:
                    self.user_configuration = await OrganizationConfigurationModel.find_one(
                        OrganizationConfigurationModel.affiliation == self.user_email
                    )
                case _:
                    self.user_configuration = None

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
        return self.user_instance.title

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
            return user
        self.not_found('email not registered')

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

    @staticmethod
    async def send_mail(email: str, subject: str, email_body: str) -> bool:
        async with IntegrationApiCommonController() as isa_c:
            return await isa_c.send_mail(email, subject, email_body)

    @staticmethod
    def keys():
        return 'category', 'code', 'message', 'data'

    def __getitem__(self, item):
        return getattr(self, item)

    @staticmethod
    def get_last_times(
            num: int, category: str = 'month', date: datetime = None, reverse: bool = False
    ) -> list[str, ...]:
        latest_cycle_list = []
        current_date = date if date else datetime.now()
        for i in range(num):
            delta, date_f_string = {
                'month': (relativedelta(months=i), '%Y-%m'),
                'day': (relativedelta(days=i), '%Y-%m-%d')
            }.get(category, (None, None))
            billing_cycle = (current_date - delta).strftime(date_f_string)
            latest_cycle_list.append(billing_cycle)
        if reverse:
            latest_cycle_list.reverse()
        return latest_cycle_list


class BaseOssViewModel(BaseViewModel):

    def __init__(self, request: Request = None, need_auth: bool = True, access_title: list[UserTitleEnum] = None):
        super().__init__(request, need_auth, access_title)
        self.root = ''

    @abc.abstractmethod
    async def before(self):
        pass

    @staticmethod
    async def gen_access_url(file_path: str | list[str]) -> list[str] | str:
        async with AliCloudOssBucketController() as ob_c:
            return f'{ob_c.access_url_prefix}{file_path}' if isinstance(file_path, str) else [
                f'{ob_c.access_url_prefix}{path}' for path in file_path
            ]

    @staticmethod
    async def get_b64_object(file_path: str, file_type: Any) -> str:
        async with AliCloudOssBucketController() as ob_c:
            return await ob_c.get_object_with_base64_async(
                file_path=file_path, file_type=file_type
            )

    @staticmethod
    async def generate_object_access_url(file_path: str, expire: int = 60) -> str:
        async with AliCloudOssBucketController() as ob_c:
            return await ob_c.generate_object_access_url_async(
                file_path=file_path, expire=expire
            )


class BaseUserCertificateOssViewModel(BaseOssViewModel):

    def __init__(self, request: Request = None, need_auth: bool = True, access_title: list[UserTitleEnum] = None):
        super().__init__(request, need_auth, access_title)
        self.root = 'org-certification'

    @abc.abstractmethod
    async def before(self):
        pass

    async def send_mail_to_affiliation(self, affiliation: EmailStr, name: str):
        email_body = render_template(
            'email/certificate-approval-required.html',
            admin_email=affiliation, org_name=name, approve_url=f'{get_settings().FRONTEND_DOMAIN}/applications'
        )
        await self.send_mail(
            affiliation, 'The New Organization Certificate Needs Your Approval', email_body
        )


class BaseEventOssViewModel(BaseOssViewModel):

    def __init__(self, request: Request = None, need_auth: bool = True, access_title: list[UserTitleEnum] = None):
        super().__init__(request, need_auth, access_title)
        self.root = 'org-events'

    @abc.abstractmethod
    async def before(self):
        pass

    @staticmethod
    async def get_event_puck_render_pages(pages_render_path) -> dict:
        async with AliCloudOssBucketController() as ob_c:
            render_resource = await ob_c.get_object_async(pages_render_path)
            resource_content: bytes = render_resource.read()
            return json.loads(resource_content.decode('utf-8'))

    @staticmethod
    async def update_event_puck_render_pages(pages_render_path: str, page_render: dict):
        async with AliCloudOssBucketController() as ob_c:
            return await ob_c.put_object_async(pages_render_path, json.dumps(page_render).encode())


class BasePaymentProductOssViewModel(BaseOssViewModel):

    def __init__(self, request: Request = None, need_auth: bool = True, access_title: list[UserTitleEnum] = None):
        super().__init__(request, need_auth, access_title)
        self.root = 'payment-product'

    @abc.abstractmethod
    async def before(self):
        pass


class BaseAccountAvatarOssViewModel(BaseOssViewModel):

    def __init__(self, request: Request = None, need_auth: bool = True, access_title: list[UserTitleEnum] = None):
        super().__init__(request, need_auth, access_title)
        self.root = 'account-avatar'

    @abc.abstractmethod
    async def before(self):
        pass

    async def get_user_b64_avatar(self, avatar_info: ImageFileType) -> str:
        return await self.get_b64_object(avatar_info.file_path, avatar_info.file_type)


class BasePaymentViewModel(BaseOssViewModel):

    def __init__(
            self, payment_gateway: PaymentGatewayEnum, request: Request = None, need_auth: bool = True
    ):
        BaseViewModel.__init__(self, request, need_auth, access_title=[UserTitleEnum.ADMIN, UserTitleEnum.ORGANIZATION])
        self.payment_gateway = payment_gateway

    @abc.abstractmethod
    async def before(self):
        await super().before()

    @asynccontextmanager
    async def payment_execution(self, *args, **kwargs) -> MLPGTransactionApiController:
        payment_gateway_category = self.user_configuration.get_payment_gateway_configuration(
            self.payment_gateway
        )
        if not payment_gateway_category:
            self.not_found('payment gateway not exist')
        if not (authorization := payment_gateway_category.authorization):
            self.not_found('payment gateway authorization not exist')
        async with MLPGTransactionApiController(
                self.payment_gateway, authorization.get('publicKey', ''), authorization.get('secretKey', ''),
                *args, **kwargs
        ) as controller:
            yield controller

    @staticmethod
    async def get_payment_gateway_authorization(
            category: PaymentGatewayEnum, origin_authorization: dict
    ) -> tuple[str, str, dict]:
        p_key, s_key, authorization = '', '', {}
        match category:
            case PaymentGatewayEnum.STRIPE:
                p_key = origin_authorization.get('publicKey', '')
                s_key = origin_authorization.get('secretKey', '')
                authorization = {'publicKey': p_key, 'secretKey': s_key}
        return p_key, s_key, authorization
