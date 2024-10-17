from fastapi import Request, UploadFile
from pydantic import EmailStr

from app.config import get_settings
from app.forms.account import *
from app.libs.cloud_provider import AliCloudOssBucketController
from app.libs.custom import render_template, encrypt
from app.libs.integration_api_controller import IntegrationApiCommonController
from app.models.account import UserTitleEnum, UserStatusEnum, CertificationItemFileType, SupportCertificateMIMEType
from app.models.common import UserModel
from app.models.account.organization import OrganizationCertificationModel
from app.response.account import AccountLoginResponseData
from app.view_models import BaseViewModel, BaseAccountAvatarOssViewModel, BaseUserCertificateOssViewModel

__all__ = (
    'RegisterViewModel',
    'UserLoginViewModel',
    'UserLogoutViewModel',
    'GetUserInfoViewModel',
    'GetUserInfoListViewModel',
    'ChangeUserStatusViewModel',
    'SendVerificationCodeViewModel',
)


class RegisterViewModel(BaseUserCertificateOssViewModel):

    def __init__(
            self, email: EmailStr, name: str, username: str, password: str, v_code: str, certificate: list[UploadFile]
    ):
        super().__init__(need_auth=False)
        self.email = email
        self.name = name
        self.username = username
        self.password = password
        self.v_code = v_code
        self.certificate_file_list = certificate

    async def before(self):
        await self.register()

    async def register(self):
        email = self.email.lower()
        if await UserModel.find_one(UserModel.email == email):
            self.forbidden('email already registered')
        async with IntegrationApiCommonController() as isa_c:
            if not await isa_c.verify_email_code(email, self.v_code):
                self.operating_failed('verification code not match')
        if not (admin := await UserModel.find_one(UserModel.title == UserTitleEnum.ADMIN)):
            self.forbidden('there is no supper admin account')
        user_info = await UserModel.insert_one(UserModel(
            email=email, name=self.name, username=self.username, title=UserTitleEnum.ORGANIZATION,
            password=encrypt(self.password, get_settings().ENCRYPT_KEY),
            status=UserStatusEnum.NEEDS_APPROVAL, affiliation=admin.email
        ))
        certificate = await OrganizationCertificationModel.insert_one(OrganizationCertificationModel(
            affiliation=user_info.email
        ))
        await self.upload_certificate(user_info, certificate)
        if (await OrganizationCertificationModel.get(certificate.id)).in_place:
            await self.send_mail_to_affiliation(user_info.affiliation, user_info.name)
        self.operating_successfully('registered successfully')

    async def upload_certificate(self, user: UserModel, certificate: OrganizationCertificationModel):
        async with AliCloudOssBucketController() as ob_c:
            identification_document, event_creation_licence_document, business_registration_certificate = self.certificate_file_list
            await certificate.update_fields(
                identification_document=await self.upload_file(
                    user, ob_c, 'identification_document', identification_document
                ),
                event_creation_licence_document=await self.upload_file(
                    user, ob_c, 'event_creation_licence_document', event_creation_licence_document
                ),
                business_registration_certificate=await self.upload_file(
                    user, ob_c, 'business_registration_certificate', business_registration_certificate
                )
            )

    async def upload_file(
            self, user: UserModel, controller: AliCloudOssBucketController, filename: str, file: UploadFile
    ) -> CertificationItemFileType:
        file_type = SupportCertificateMIMEType.check_value_exists(file.content_type)
        *_, file_extension = file_type.value.split('/')
        path = f'{self.root}/{user.id}/{filename}.{file_extension}'
        file_body = await file.read()
        upload_result = await controller.put_object_async(path, file_body)
        if upload_result and upload_result.crc:
            return CertificationItemFileType(file_path=path, file_type=file_type)
        self.operating_failed(f'{filename} upload file failed')


class UserLoginViewModel(BaseAccountAvatarOssViewModel):
    def __init__(self, form_data: LoginForm):
        super().__init__(need_auth=False)
        self.form_data = form_data

    async def before(self):
        await self.login()

    async def login(self):
        if not (user := await self.get_user_instance(self.form_data.email.lower())):
            self.operating_failed('email not registered')
        if user.password is None:
            self.operating_failed('password not set')
        if not user.check_password(self.form_data.password):
            self.operating_failed('password not matched')
        self.operating_successfully(AccountLoginResponseData(
            message='login successfully',
            token=self.create_token(user.email, user.email, user.title),
            email=user.email,
            name=user.name,
            username=user.username,
            title=user.title.name.title(),
            avatar=await self.gen_access_url(user.avatar.file_path),
            affiliation=user.affiliation if user.title != UserTitleEnum.ADMIN else None
        ))


class UserLogoutViewModel(BaseViewModel):

    def __init__(self, request: Request):
        super().__init__(request=request)

    async def before(self):
        self.logout()

    def logout(self):
        self.operating_successfully('logged out successfully')


class GetUserInfoViewModel(BaseAccountAvatarOssViewModel):
    def __init__(self, request: Request):
        super().__init__(request=request)

    async def before(self):
        self.operating_successfully(
            self.user_instance.information | {'avatar': await self.gen_access_url(self.user_instance.avatar.file_path)}
        )


class GetUserInfoListViewModel(BaseAccountAvatarOssViewModel):
    def __init__(self, request: Request):
        super().__init__(request=request, access_title=[UserTitleEnum.ADMIN, UserTitleEnum.ORGANIZATION])

    async def before(self):
        self.operating_successfully([await self.get_user_info(user) async for user in UserModel.find(
            UserModel.affiliation == self.user_email
        )])

    async def get_user_info(self, user: UserModel):
        return user.information | {'avatar': await self.gen_access_url(user.avatar.file_path)}


class ChangeUserStatusViewModel(BaseViewModel):
    def __init__(self, email: str, enable: bool, reason: str, request: Request):
        super().__init__(request=request, access_title=[UserTitleEnum.ADMIN, UserTitleEnum.ORGANIZATION])
        self.email = email
        self.enable = enable
        self.reason = reason

    async def before(self):
        if not (user := await UserModel.find_one(
                UserModel.email == self.email, UserModel.affiliation == self.user_email
        )):
            self.not_found('user not found')
        if user.status == UserStatusEnum.NEEDS_APPROVAL:
            self.forbidden('user needs approval first')
        if user.status == UserStatusEnum.ACTIVE if self.enable else UserStatusEnum.DISABLED:
            self.forbidden(f'user already in {"enabled" if self.enable else "disabled"}')
        await user.update_fields(status=UserStatusEnum.ACTIVE if self.enable else UserStatusEnum.DISABLED)
        async with IntegrationApiCommonController() as isa_c:
            email_body = render_template(
                'email/user-modify-reason.html',
                email=user.email, affiliation=self.user_instance.affiliation,
                status=(UserStatusEnum.ACTIVE if self.enable else UserStatusEnum.DISABLED).name.title(),
                reason=self.reason
            )
            await isa_c.send_mail(user.email, 'Account Status Changed', email_body)
        self.operating_successfully(
            f'status of user {self.email} changed to {"Enabled" if self.enable else "Disabled"} successfully'
        )


class SendVerificationCodeViewModel(BaseViewModel):
    def __init__(self, email: str):
        super().__init__(need_auth=False)
        self.email = email

    async def before(self):
        await self.send_email_v_code()

    async def send_email_v_code(self):
        async with IntegrationApiCommonController() as isa_c:
            if await isa_c.send_email_validation_code(self.email):
                self.operating_successfully('verification code sent')
        self.operating_failed('failed to send verification code')
