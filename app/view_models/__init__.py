import abc
import json
from datetime import datetime

from dateutil.relativedelta import relativedelta
from faker.proxy import Faker
from fastapi import Request, BackgroundTasks, UploadFile
from httpx import TimeoutException

from app.config import get_settings
from app.libs.cache import RedisCacheController
from app.libs.cloud_provider import AzureBlobController, AzureBlobUploadResult
from app.libs.constants import ResponseStatusCodeEnum, get_response_message
from app.libs.custom import cus_print
from app.models import SupportImageMIMEType
from app.models.account import UserModel, UserProfile, AdminRoleEnum, AdminProfile, AdminModel, UserTitleEnum
from app.response import ResponseModel

__all__ = (
    'ViewModelException',
    'ViewModelRequestException',
    'BaseViewModel',
    'BaseAdminViewModel',
    'BaseOssViewModel',
    'BaseWebsiteOssViewModel',
)


class ViewModelException(Exception):
    pass


class ViewModelRequestException(ViewModelException):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class BaseViewModel(RedisCacheController):

    def __init__(
            self, request: Request = None, user_profile: UserProfile | AdminProfile = None,
            access_title: list[UserTitleEnum | AdminRoleEnum] = None, bg_tasks: BackgroundTasks = None
    ):
        super().__init__()
        self.request: Request = request
        self.bg_tasks: BackgroundTasks = bg_tasks
        self.user_profile: UserProfile | AdminProfile = user_profile
        self.user_instance: UserModel | AdminModel = None
        self.access_title: UserTitleEnum | AdminRoleEnum = access_title
        self.faker = Faker()
        self.category = get_settings().APP_NO
        self.code = ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY.value
        self.message = get_response_message(ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY)
        self.data = None
        self.redis: RedisCacheController = None

    async def __aenter__(self):
        try:
            async with RedisCacheController() as cache:
                self.redis = cache
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

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.after()
        if exc_type:
            cus_print(f'{exc_type}: {exc_val}', )
        return True

    @abc.abstractmethod
    async def before(self):
        if self.user_profile:
            self.user_instance = await UserModel.find_one(UserModel.ssoUid == self.user_profile.ssouid)
        if self.access_title:
            if not self.user_instance:
                self.forbidden('User not have access')
            if self.user_instance.title not in self.access_title:
                self.forbidden('User not have access')

    async def after(self):
        pass

    @property
    def user_email(self):
        return self.user_instance.email

    @property
    def user_title(self):
        return self.user_instance.title

    def operating_successfully(self, data: str | dict | list, handled: bool = False):
        self.code = ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY.value
        self.message = get_response_message(ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY)
        self.data = data
        if handled:
            return
        raise ViewModelRequestException(message=data)

    def empty_content(self, data: str | dict | list, handled: bool = False):
        self.code = ResponseStatusCodeEnum.EMPTY_CONTENT.value
        self.message = get_response_message(ResponseStatusCodeEnum.EMPTY_CONTENT)
        self.data = data
        if handled:
            return
        raise ViewModelRequestException(message=data)

    def nothing_changed(self, data: str | dict | list, handled: bool = False):
        self.code = ResponseStatusCodeEnum.NOTHING_CHANGED.value
        self.message = get_response_message(ResponseStatusCodeEnum.NOTHING_CHANGED)
        self.data = data
        if handled:
            return
        raise ViewModelRequestException(message=data)

    def operating_failed(self, msg: str, handled: bool = False):
        self.code = ResponseStatusCodeEnum.OPERATING_FAILED.value
        self.message = get_response_message(ResponseStatusCodeEnum.OPERATING_FAILED)
        self.data = msg
        if handled:
            return
        raise ViewModelRequestException(message=msg)

    def unauthorized(self, msg: str, handled: bool = False):
        self.code = ResponseStatusCodeEnum.UNAUTHORIZED.value
        self.message = get_response_message(ResponseStatusCodeEnum.UNAUTHORIZED)
        self.data = msg
        if handled:
            return
        raise ViewModelRequestException(message=msg)

    def forbidden(self, msg: str, handled: bool = False):
        self.code = ResponseStatusCodeEnum.FORBIDDEN.value
        self.message = get_response_message(ResponseStatusCodeEnum.FORBIDDEN)
        self.data = msg
        if handled:
            return
        raise ViewModelRequestException(message=msg)

    def not_found(self, msg: str, handled: bool = False):
        self.code = ResponseStatusCodeEnum.NOT_FOUND.value
        self.message = get_response_message(ResponseStatusCodeEnum.NOT_FOUND)
        self.data = msg
        if handled:
            return
        raise ViewModelRequestException(message=msg)

    def illegal_parameters(self, msg: str, handled: bool = False):
        self.code = ResponseStatusCodeEnum.ILLEGAL_PARAMETERS.value
        self.message = get_response_message(ResponseStatusCodeEnum.ILLEGAL_PARAMETERS)
        self.data = msg
        if handled:
            return
        raise ViewModelRequestException(message=msg)

    def request_timeout(self, msg: str, handled: bool = False):
        self.code = ResponseStatusCodeEnum.REQUEST_TIMEOUT.value
        self.message = get_response_message(ResponseStatusCodeEnum.REQUEST_TIMEOUT)
        self.data = msg
        if handled:
            return
        raise ViewModelRequestException(message=msg)

    def system_error(self, msg: str, handled: bool = False):
        self.code = ResponseStatusCodeEnum.SYSTEM_ERROR.value
        self.message = get_response_message(ResponseStatusCodeEnum.SYSTEM_ERROR)
        self.data = msg
        if handled:
            return
        raise ViewModelRequestException(message=msg)

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


class BaseAdminViewModel(BaseViewModel):

    def __init__(
            self, request: Request = None, user_profile: AdminProfile = None,
            access_title: list[AdminRoleEnum] = None, bg_tasks: BackgroundTasks = None
    ):
        super().__init__(request, user_profile, access_title, bg_tasks)

    @abc.abstractmethod
    async def before(self):
        if self.user_profile:
            self.user_instance = await AdminModel.find_one(AdminModel.email == self.user_profile.email)
        if not self.user_instance:
            self.forbidden('User not found')
        if self.access_title and self.user_instance.role not in self.access_title:
            self.forbidden('User not have access')


class BaseOssViewModel:

    def __init__(self):
        self.root = ''

    @staticmethod
    async def generate_access_url(file_path: str | list[str]) -> list[str] | str:
        async with AzureBlobController() as ab_c:
            if isinstance(file_path, str):
                return ab_c.generate_access_url(file_path)
            return [ab_c.generate_access_url(path) for path in file_path]

    @staticmethod
    async def upload_file(file_path: str, data: bytes | str, overwrite: bool = True) -> AzureBlobUploadResult:
        async with AzureBlobController() as ab_c:
            return await ab_c.upload_file(file_path, data, overwrite)

    @staticmethod
    async def delete_file(file_path: str):
        async with AzureBlobController() as ab_c:
            return await ab_c.delete_file(file_path)

    async def upload_image(
            self, parent: str, img_id: str, file: UploadFile, file_type: SupportImageMIMEType
    ) -> tuple[str, AzureBlobUploadResult | None]:
        *_, file_extension = file_type.value.split('/')
        file_body = await file.read()
        file_path = f'{self.root}/{parent}/{img_id}.{file_extension}'
        upload_result = await self.upload_file(file_path, file_body)
        if upload_result and upload_result:
            return file_path, upload_result
        return file_path, None


class BaseWebsiteOssViewModel(BaseAdminViewModel, BaseOssViewModel):

    def __init__(
            self, request: Request = None, user_profile: UserProfile = None, access_title: list[AdminRoleEnum] = None
    ):
        super().__init__(request=request, user_profile=user_profile, access_title=access_title)
        self.root = 'websites'

    @abc.abstractmethod
    async def before(self):
        await super().before()

    @staticmethod
    async def get_website_puck_render_pages(pages_render_path) -> dict:
        async with AzureBlobController() as ab_c:
            render_resource = await ab_c.get_object_async(pages_render_path)
            resource_content: bytes = render_resource.read()
            return json.loads(resource_content.decode('utf-8'))

    @staticmethod
    async def update_website_puck_render_pages(pages_render_path: str, page_render: dict):
        async with AzureBlobController() as ab_c:
            return await ab_c.put_object_async(pages_render_path, json.dumps(page_render).encode())
