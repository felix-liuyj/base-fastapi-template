from fastapi import Request, UploadFile
from pydantic import EmailStr

from app.forms.payment import BindNewOrganizationPaymentForm
from app.libs.cloud_provider import AliCloudOssBucketController
from app.libs.mlpg_api_controller import MLPGTransactionApiController
from app.models.account import (
    OrganizationDocumentEnum, CertificationItemFileType, UserTitleEnum, SupportCertificateMIMEType,
    AdminPaymentGatewayType
)
from app.models.account.admin import AdminConfigurationModel
from app.models.account.organization import (
    OrganizationConfigurationModel, OrganizationCertificationModel, OrganizationPaymentGatewayConfigurationType,
    OrganizationPaymentGatewayType
)
from app.models.payment import PaymentAuthorizationEnvEnum
from app.response.payment import (
    OrganizationEnabledPaymentResponseDataItem, OrganizationAddedPaymentResponseDataItem,
    OrganizationAddedPaymentResponseDataItemEnv
)
from app.view_models import (
    BaseOssViewModel, BaseUserCertificateOssViewModel, BasePaymentViewModel
)

__all__ = (
    'GetOrganizationConfigurationViewModel',
    'GetOrganizationEnabledPaymentViewModel',
    'GetOrganizationAddedPaymentViewModel',
    'BindNewOrganizationPaymentViewModel',
    'UploadOrganizationCertificateViewModel',
    'GetOrganizationCertificateViewModel',
)


class GetOrganizationConfigurationViewModel(BaseOssViewModel):

    def __init__(self, request: Request):
        super().__init__(request, access_title=[UserTitleEnum.ORGANIZATION])
        self.root = 'payment_gateway'

    async def before(self):
        await self.get_org_configuration()

    async def get_org_configuration(self):
        if not (config := await OrganizationConfigurationModel.find_one(
                OrganizationConfigurationModel.affiliation == self.user_email
        )):
            config = await OrganizationConfigurationModel.insert_one(OrganizationConfigurationModel(
                affiliation=self.user_email
            ))
        self.operating_successfully(config.information | {'payment_gateway': {key: val.model_dump() | {
            'image': await self.gen_access_url(file_path=val.image)
        } for key, val in config.payment_gateway.items()}})


class GetOrganizationEnabledPaymentViewModel(BaseOssViewModel):

    def __init__(self, request: Request):
        super().__init__(request, access_title=[UserTitleEnum.ORGANIZATION])
        self.root = 'payment_gateway'

    async def before(self):
        await self.get_org_enabled_payment()

    async def get_org_enabled_payment(self):
        if not (config := await AdminConfigurationModel.find_one(
                AdminConfigurationModel.affiliation == self.user_instance.affiliation
        )):
            self.not_found('there are no enabled payment gateway for this account')
        self.operating_successfully([OrganizationEnabledPaymentResponseDataItem(
            key=key, name=val.name, logo=await self.gen_access_url(file_path=val.image)
        ) for key, val in config.payment_gateway.items() if val.enable])


class GetOrganizationAddedPaymentViewModel(BaseOssViewModel):

    def __init__(self, request: Request):
        super().__init__(request, access_title=[UserTitleEnum.ORGANIZATION])
        self.root = 'payment_gateway'

    async def before(self):
        await self.get_org_enabled_payment()

    async def get_org_enabled_payment(self):
        if not (config := await OrganizationConfigurationModel.find_one(
                OrganizationConfigurationModel.affiliation == self.user_instance.email
        )):
            self.operating_successfully([])
        self.operating_successfully([OrganizationAddedPaymentResponseDataItem(
            key=key, name=val.name, enabled=val.enable,
            env=OrganizationAddedPaymentResponseDataItemEnv(
                enabled=[PaymentAuthorizationEnvEnum(env) for env in val.configuration.keys()],
                current=val.env,
            ), logo=await self.gen_access_url(file_path=val.image),
            methods=config.get_payment_gateway_configuration(key).methods
        ) for key, val in config.payment_gateway.items()])


class BindNewOrganizationPaymentViewModel(BasePaymentViewModel):

    def __init__(self, form_data: BindNewOrganizationPaymentForm, request: Request):
        super().__init__(payment_gateway=form_data.category, request=request)
        self.root = 'payment_gateway'
        self.form_data = form_data

    async def before(self):
        await self.create_new_payment_gateway()

    async def create_new_payment_gateway(self):
        if not (admin_config := await AdminConfigurationModel.find_one(
                AdminConfigurationModel.affiliation == self.user_instance.affiliation
        )):
            self.not_found('there are no enabled payment gateway for this account')
        if not (payment_gateway_category := admin_config.payment_gateway.get(self.form_data.category.value)):
            self.forbidden('payment gateway category not enabled')
        if not payment_gateway_category.enable:
            self.forbidden('payment gateway category not enabled')
        if not (config := await OrganizationConfigurationModel.find_one(
                OrganizationConfigurationModel.affiliation == self.user_email
        )):
            config = await OrganizationConfigurationModel.insert_one(OrganizationConfigurationModel(
                affiliation=self.user_email
            ))
        await self.add_new_payment_gateway_to_configuration(config, payment_gateway_category)
        self.operating_successfully('payment gateway added successfully')

    async def add_new_payment_gateway_to_configuration(
            self, config: OrganizationConfigurationModel, payment_gateway_category: AdminPaymentGatewayType
    ):
        p_key, s_key, authorization = await self.get_payment_gateway_authorization(
            self.form_data.category, self.form_data.authorization
        )
        async with MLPGTransactionApiController(self.form_data.category, p_key, s_key) as mlpg_api:
            if not (payment_method_data := await mlpg_api.get_payment_method_list(available=True)):
                self.forbidden('payment gateway authorization failed')
            payment_method_config = OrganizationPaymentGatewayType(
                env=self.form_data.env,
                name=self.form_data.category.name.title(),
                image=payment_gateway_category.image,
                enable=True
            )
            payment_method_config.configuration.update({
                self.form_data.env.value: OrganizationPaymentGatewayConfigurationType(
                    methods=payment_method_data.get('methods', []), authorization=authorization
                )
            })
            await config.update_fields(payment_gateway={self.form_data.category.value: payment_method_config})


class UploadOrganizationCertificateViewModel(BaseUserCertificateOssViewModel):
    def __init__(self, category: OrganizationDocumentEnum, file: UploadFile, request: Request):
        super().__init__(request=request, access_title=[UserTitleEnum.ORGANIZATION])
        self.category = category
        self.file = file
        self.file_type: SupportCertificateMIMEType = None

    async def before(self):
        await self.validate_filename()
        await self.upload_certificate()

    async def validate_filename(self):
        self.file_type = SupportCertificateMIMEType.check_value_exists(self.file.content_type)
        if not self.file_type:
            self.forbidden('unsupported file type')

    async def upload_certificate(self):
        async with AliCloudOssBucketController() as ob_c:
            if not (org_cert := await OrganizationCertificationModel.find_one(
                    OrganizationCertificationModel.affiliation == self.user_email
            )):
                self.not_found('organization certificate not found')
            *_, file_extension = self.file_type.value.split('/')
            path = f'{self.root}/{self.user_instance.name}/{self.category.name.lower()}.{file_extension}'
            file_body = await self.file.read()
            upload_result = await ob_c.put_object_async(path, file_body)
            if upload_result:
                certification_item = CertificationItemFileType(file_path=path, file_type=self.file_type)
                await org_cert.update_fields(**{self.category.name.lower(): certification_item})
                if org_cert.in_place:
                    await self.send_mail_to_affiliation(self.user_instance.affiliation, self.user_instance.name)
                self.operating_successfully({
                    'message': f'{self.category.name.lower().replace("_", " ")}upload successfully',
                    'crc64': upload_result.crc
                })
            self.operating_failed(f'{self.category.name.lower().replace("_", " ")}upload failed')


class GetOrganizationCertificateViewModel(BaseUserCertificateOssViewModel):
    def __init__(self, email: EmailStr, category: OrganizationDocumentEnum, download_file: bool, request: Request):
        super().__init__(request=request, access_title=[UserTitleEnum.ADMIN, UserTitleEnum.ORGANIZATION])
        self.email = email or ''
        self.category = category
        self.download_file = download_file

    async def before(self):
        await self.get_certificate()

    async def get_certificate(self):
        cert_query_condition = []
        match self.user_title:
            case UserTitleEnum.ADMIN:
                cert_query_condition.append(OrganizationCertificationModel.affiliation == self.email.lower())
            case UserTitleEnum.ORGANIZATION:
                cert_query_condition.append(OrganizationCertificationModel.affiliation == self.user_email)
            case _:
                self.forbidden('operation not allowed')
        if not (certification := await OrganizationCertificationModel.find_one(
                OrganizationCertificationModel.affiliation == (self.email.lower() if self.email else self.user_email)
        )):
            self.not_found('certificate not found')
        if not (certification_item := getattr(certification, self.category.name.lower())):
            self.not_found('certificate not found')
        if self.download_file:
            file_body = await self.generate_object_access_url(file_path=certification_item.file_path)
        else:
            file_body = await self.get_b64_object(
                file_path=certification_item.file_path, file_type=certification_item.file_type
            )
        self.operating_successfully(file_body)
