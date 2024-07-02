import bcrypt
from fastapi import Request, UploadFile
from httpx import TimeoutException
from requests import ReadTimeout

from app.config import get_settings
from app.forms.common import *
from app.libs.cloud_provider import AliCloudOssBucketController
from app.libs.custom import render_template
from app.models.user import UserModel, SupportCertificateMIMEType, CertificationType, CertificationItemType
from app.view_models import BaseViewModel, BaseCertificateOssViewModel

__all__ = (
    'RegisterViewModel',
    'GetUserInfoViewModel',
    'SendVerificationCodeViewModel',
    'VerifyEmailViewModel',
    'UploadFileViewModel',
    'GetFileViewModel',
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


class UploadFileViewModel(BaseCertificateOssViewModel):
    def __init__(self, category: str, file: UploadFile, request: Request):
        super().__init__(request=request)
        self.category = category
        self.file = file
        self.file_type: SupportCertificateMIMEType = None

    async def before(self):
        try:
            await self.validate_category()
            await self.validate_filename()
            await self.upload_certificate()
        except ReadTimeout as e:
            self.request_timeout(str(e))

    async def validate_category(self):
        supported_categories = [
            'category'
        ]
        if self.category not in supported_categories:
            self.forbidden('unsupported category')

    async def validate_filename(self):
        self.file_type = SupportCertificateMIMEType.check_value_exists(self.file.content_type)
        if not self.file_type:
            self.forbidden('unsupported file type')

    async def upload_certificate(self):
        async with AliCloudOssBucketController(
                access_key=get_settings().ALI_OSS_ACCESS_KEY, access_secret=get_settings().ALI_OSS_ACCESS_SECRET,
                region_id=get_settings().ALI_OSS_REGION, bucket_name=get_settings().ALI_OSS_BUCKET_NAME
        ) as ob_c:
            *_, file_extension = self.file_type.value.split('/')
            path = f'{self.root}/{self.user_instance.name}/{self.category}.{file_extension}'
            file_body = await self.file.read()
            upload_result = await ob_c.put_object_async(path, file_body)
            if upload_result:
                if not (certification := self.user_instance.certification):
                    certification = CertificationType()
                certification_item = CertificationItemType(file_path=path, file_type=self.file_type)
                setattr(certification, self.category, certification_item)
                await self.user_instance.update_fields(certification=certification)
                if certification.in_place:
                    await self.send_mail_to_affiliation()
                self.operating_successfully({
                    'message': f'{self.category.replace("_", " ")}upload successfully',
                    'crc64': upload_result.crc
                })
            self.operating_failed(f'{self.category.replace("_", " ")}upload failed')

    async def send_mail_to_affiliation(self):
        email_body = render_template(
            'email/certificate_approval_required.html',
            admin_email=self.user_instance.affiliation, org_name=self.user_instance.name,
            approve_url=f'{get_settings().FRONTEND_DOMAIN}/applications'
        )
        await self.send_mail(
            self.user_instance.affiliation,
            'The New Organization Certificate Needs Your Approval',
            email_body
        )


class GetFileViewModel(BaseCertificateOssViewModel):
    def __init__(self, category: str, download_file: bool, request: Request):
        super().__init__(request=request)
        self.category = category
        self.download_file = download_file

    async def before(self):
        try:
            await self.validate_category()
            await self.get_certificate()
        except ReadTimeout as e:
            self.request_timeout(str(e))

    async def validate_category(self):
        supported_categories = [
            'category'
        ]
        if self.category not in supported_categories:
            self.forbidden('unsupported category')

    async def get_certificate(self):
        async with AliCloudOssBucketController(
                access_key=get_settings().ALI_OSS_ACCESS_KEY, access_secret=get_settings().ALI_OSS_ACCESS_SECRET,
                region_id=get_settings().ALI_OSS_REGION, bucket_name=get_settings().ALI_OSS_BUCKET_NAME
        ) as ob_c:
            if not (certification := self.user_instance.certification):
                self.not_found('certificate not found')
            if not (certification_item := getattr(certification, self.category)):
                self.not_found('certificate not found')
            if self.download_file:
                file_body = await ob_c.generate_object_access_url_async(file_path=certification_item.file_path)
            else:
                file_body = await ob_c.get_object_with_base64_async(
                    file_path=certification_item.file_path, file_type=certification_item.file_type
                )
            self.operating_successfully(file_body)

