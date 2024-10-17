from fastapi import Request, UploadFile

from app.forms.settings import *
from app.libs.cloud_provider import AliCloudOssBucketController
from app.libs.integration_api_controller import IntegrationApiCommonController
from app.models.account import (
    UserTitleEnum,
    SupportImageMIMEType,
    ImageFileType,
    UserModifyStatusEnum
)
from app.models.account.admin import UserModifyRequestModel
from app.models.common import UserModel
from app.view_models import BaseViewModel, BaseAccountAvatarOssViewModel

__all__ = (
    'UpdateUserViewModel',
    'UploadUserAvatarViewModel',
    'SetPasswordViewModel',
)


class UpdateUserViewModel(BaseViewModel):
    def __init__(self, form_data: UpdateUserForm, request: Request):
        super().__init__(request)
        self.form_data = form_data

    async def before(self):
        await self.update_user_information()

    async def update_user_information(self):
        async with IntegrationApiCommonController() as isa_c:
            verified_email = await isa_c.verify_email_code(self.user_email, self.form_data.vCode)
            if not verified_email or verified_email != self.user_email:
                self.operating_failed('verification code not match')

        update_field = self.form_data.model_dump(
            exclude=['vCode'], exclude_unset=True, exclude_none=True, exclude_defaults=True
        )
        update_field_keys = list(update_field.keys())
        if self.user_title == UserTitleEnum.ORGANIZATION and any([
            key in update_field_keys for key in UserModifyRequestModel.modify_fields
        ]):
            await UserModifyRequestModel.insert_one(UserModifyRequestModel(
                email=self.user_email,
                name=update_field.pop('name'),
                affiliation=self.user_instance.affiliation
            ))
        await self.user_instance.update_fields(**update_field)
        self.operating_successfully('user information update successfully')


class UploadUserAvatarViewModel(BaseAccountAvatarOssViewModel):
    def __init__(self, avatar_file: UploadFile, request: Request):
        super().__init__(request)
        self.avatar_file = avatar_file
        self.file_type: SupportImageMIMEType = None

    async def before(self):
        await self.validate_filename()
        await self.upload_user_avatar()

    async def validate_filename(self):
        self.file_type = SupportImageMIMEType.check_value_exists(self.avatar_file.content_type)
        if not self.file_type:
            self.forbidden('unsupported file type')

    async def upload_user_avatar(self):
        async with AliCloudOssBucketController() as ob_c:
            *_, file_extension = self.file_type.value.split('/')
            path = f'{self.root}/{self.user_instance.title.name.title()}/{self.user_instance.id}.{file_extension}'
            file_body = await self.avatar_file.read()
            upload_result = await ob_c.put_object_with_public_read_async(path, file_body)
            if not upload_result:
                self.operating_failed('user avatar upload failed')
            await self.user_instance.update_fields(avatar=ImageFileType(file_path=path, file_type=self.file_type))
            self.operating_successfully({
                'message': f'user avatar upload successfully',
                'crc64': upload_result.crc
            })


class GetUserModifyRequestViewModel(BaseViewModel):
    def __init__(self, request: Request):
        super().__init__(request, access_title=[UserTitleEnum.ADMIN])

    async def before(self):
        await self.get_user_modify_request_list()

    async def get_user_modify_request_list(self):
        request_list = await UserModifyRequestModel.find(
            UserModifyRequestModel.affiliation == self.user_email,
            UserModifyRequestModel.closed == False,
        ).to_list()
        self.operating_successfully([
            request.information | {key: getattr(target_user, key, '') for key in request.modify_fields}
            for request in request_list if (target_user := await UserModel.find_one(UserModel.email == request.email))
        ])


class ProcessUserModifyRequestViewModel(BaseViewModel):
    def __init__(self, form_data: ProcessUserModifyRequestForm, request: Request):
        super().__init__(request, access_title=[UserTitleEnum.ADMIN])
        self.form_data = form_data

    async def before(self):
        await self.process_user_modify_request()

    async def process_user_modify_request(self):
        if not (modify_request := await UserModifyRequestModel.get(self.form_data.requestId)):
            self.not_found('modify request not exist')
        if not (user := await UserModel.find_one(UserModel.email == modify_request.email)):
            self.not_found('user not exist')
        if modify_request.closed:
            self.forbidden('modify request already closed')
        if self.form_data.result:
            await user.update_fields(
                **modify_request.model_dump(include=modify_request.modify_fields)
            )
        await modify_request.update_fields(
            closed=True,
            status=UserModifyStatusEnum.EXECUTED if self.form_data.result else UserModifyStatusEnum.REJECTED
        )
        self.operating_successfully('user information update successfully')


class SetPasswordViewModel(BaseViewModel):
    def __init__(self, form_data: SetPasswordForm):
        super().__init__(need_auth=False)
        self.form_data = form_data

    async def before(self):
        await self.set_password()

    async def set_password(self):
        user = await self.get_user_instance(self.form_data.email.lower())
        async with IntegrationApiCommonController() as isa_c:
            if not (await isa_c.verify_email_code(user.email, self.form_data.vCode)):
                self.operating_failed('verification code not match')
        await user.update_fields(encrypt_fields={'password': self.form_data.password})
        self.operating_successfully('password reset successfully')
