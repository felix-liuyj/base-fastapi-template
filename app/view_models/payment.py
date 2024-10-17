import json
from json import JSONDecodeError
from uuid import uuid4

from beanie import PydanticObjectId
from beanie.odm.operators.find.comparison import In
from fastapi import Request, UploadFile

from app.config import get_settings
from app.forms.payment import (
    UpdatePaymentProductForm, CreatePaymentCheckoutSessionForm, CreatePaymentCheckoutSessionGoodType,
    PaymentGatewayConfigurationChangeForm
)
from app.libs.cloud_provider import AliCloudOssBucketController
from app.libs.mlpg_api_controller import PaymentGatewayEnum, MLPGTransactionApiController
from app.libs.mlpg_api_controller.transaction import (
    GetTransactionForm, CreateNewCheckoutSessionForm, SubmitTypeEnum, TransactionStatusEnum,
    TransactionCheckoutSessionLineItemType
)
from app.models import SupportImageMIMEType
from app.models.account import ImageFileType, SupportCertificateMIMEType, UserTitleEnum
from app.models.account.admin import AdminConfigurationModel
from app.models.account.organization import OrganizationConfigurationModel, OrganizationPaymentGatewayConfigurationType
from app.models.events import EventModel
from app.models.payment import (
    PaymentProductModel, PaymentProductOptionType, PaymentTransactionStatusEnum, PaymentProductAffiliationType,
    PaymentProductAffiliationBindTypeEnum
)
from app.response.payment import *
from app.view_models import BaseViewModel, BasePaymentViewModel, BasePaymentProductOssViewModel, BaseOssViewModel

__all__ = (
    'GetPaymentTransactionRecordViewModel',
    'GetPaymentProductViewModel',
    'CreatePaymentProductViewModel',
    'UpdatePaymentProductViewModel',
    'GetPaymentCheckoutSessionViewModel',
    'CreatePaymentCheckoutSessionViewModel',
    'PaymentGatewayConfigurationChangeViewModel',
    # 'GetPaymentLinkViewModel',
    # 'CreatePaymentLinkViewModel',
    'GetPaymentMethodViewModel',
    # 'GetStripePaymentPriceViewModel',
    # 'CreateStripePaymentPriceViewModel',
)


class GetPaymentTransactionRecordViewModel(BaseViewModel):
    def __init__(self, payment_gateway: PaymentGatewayEnum, status: list[TransactionStatusEnum], request: Request):
        super().__init__(request=request)
        self.payment_gateway = payment_gateway
        self.status = status

    async def before(self):
        await self.get_transaction_records()

    async def get_transaction_records(self):
        async with MLPGTransactionApiController(self.payment_gateway, '', '') as mlpg_c:
            form = GetTransactionForm()
            if self.payment_gateway is not None:
                form.gateway = self.payment_gateway
            if self.status is not None:
                form.status = self.status
            records = await mlpg_c.get_transaction(form)
            if not isinstance(records, list):
                self.operating_failed(records)
            self.operating_successfully([PaymentTransactionQueryResponseDataItem(
                amount=record.get('amount', 0.0),
                attribution=record.get('attribution', ''),
                createdAt=record.get('createdAt', ''),
                currency=record.get('currency', ''),
                gateway=PaymentGatewayEnum.check_value_exists(record.get('gateway')),
                id=record.get('id', ''),
                metadata=record.get('metadata', {}),
                sessionId=record.get('session_id', ''),
                status=PaymentTransactionStatusEnum.check_value_exists(record.get('status', '')),
                updatedAt=record.get('updatedAt', ''),
            ) for record in records])


class GetPaymentProductViewModel(BasePaymentProductOssViewModel):
    def __init__(self, product_id: str, bind_id: str = '', request: Request = None):
        super().__init__(request=request)
        self.product_id = product_id
        self.bind_id = bind_id

    async def before(self):
        await self.get_payment_product()

    async def get_payment_product(self):
        if self.product_id:
            if not (product := await PaymentProductModel.get(self.product_id)):
                self.not_found('payment product not exist')
            product_list = [product]
        else:
            condition = [PaymentProductModel.affiliation.creator == self.user_email]
            if self.bind_id:
                condition.append(PaymentProductModel.affiliation.bindId == self.bind_id)
            product_list = await PaymentProductModel.find(*condition).to_list()
        if not len(product_list) - 1:
            if product_list[0].affiliation.bindType == PaymentProductAffiliationBindTypeEnum.EVENT:
                self.operating_successfully(await self.generate_product_response(product_list[0]))
        self.operating_successfully([await self.generate_product_response(product) for product in product_list])

    async def generate_product_response(self, product: PaymentProductModel):
        min_u, max_u = product.unit_amount_range
        return PaymentProductQueryResponseDataItem(
            id=product.sid,
            name=product.name,
            briefDescription=product.briefDescription,
            detailedDescription=product.detailedDescription,
            images=await self.gen_access_url([image.file_path for image in product.images]),
            stocks=product.stocks,
            options=list(product.options.values()),
            unitAmountRange=ProductQueryResponseDataItemUnitAmountRange(min=min_u, max=max_u),
        )


class CreatePaymentProductViewModel(BasePaymentProductOssViewModel):
    def __init__(
            self, name: str, brief_description: str, detailed_description: str, images: list[UploadFile],
            bind_id: str = '', options: list[str] = None, request: Request = None
    ):
        super().__init__(request=request)
        self.product_name = name
        self.product_brief_description = brief_description
        self.product_detailed_description = detailed_description
        self.images = images
        self.bind_id = bind_id
        self.options = self.parse_options(options or [])

    async def before(self):
        await self.create_payment_product()

    def parse_options(self, options: list[str]) -> list[PaymentProductOptionType]:
        try:
            return [PaymentProductOptionType(**json.loads(option)) for option in options]
        except JSONDecodeError:
            self.illegal_parameters('invalid options')

    async def create_payment_product(self):
        product = await PaymentProductModel.insert_one(PaymentProductModel(
            name=self.product_name, affiliation=PaymentProductAffiliationType(
                creator=self.user_email, bindId=self.bind_id,
                bindType=PaymentProductAffiliationBindTypeEnum.E_COMMERCE
            ), briefDescription=self.product_brief_description,
            detailedDescription=self.product_detailed_description,
            images=[], options={option.value: option for option in self.options}
        ))
        product_image_list = await self.upload_images(product)
        await product.update_fields(images=product_image_list)
        self.operating_successfully(PaymentProductCreateResponseData(ok=True, id=product.sid))

    async def upload_images(self, product: PaymentProductModel):
        container: list[ImageFileType] = []
        async with AliCloudOssBucketController() as ob_c:
            for index, image in enumerate(self.images):
                file_type = SupportImageMIMEType.check_value_exists(image.content_type)
                *_, file_extension = file_type.value.split('/')
                path = f'{self.root}/{product.id}/{index}.{file_extension}'
                file_body = await image.read()
                upload_result = await ob_c.put_object_with_public_read_async(path, file_body)
                if upload_result and upload_result.crc:
                    container.append(ImageFileType(file_path=path, file_type=file_type))
                else:
                    self.operating_failed(f'{image.filename} upload image failed')
            return container


class UpdatePaymentProductViewModel(BasePaymentProductOssViewModel):
    def __init__(self, form_data: UpdatePaymentProductForm, images: list[UploadFile], request: Request):
        super().__init__(request=request)
        self.form_data = form_data
        self.images = images

    async def before(self):
        await self.update_payment_product()

    async def update_payment_product(self):
        if not (product := await PaymentProductModel.get(self.form_data.product_id)):
            self.not_found('payment product not exist')
        if self.images:
            await self.upload_image(product)
        await product.update_fields(**self.form_data.model_dump(
            exclude=['productId'], exclude_defaults=True, exclude_none=True, exclude_unset=True
        ))
        self.operating_successfully('payment product updated successfully')

    async def upload_image(self, product: PaymentProductModel):
        async with AliCloudOssBucketController() as ob_c:
            start_index = len(product.images)
            for image in self.images:
                file_type = SupportCertificateMIMEType.check_value_exists(image.content_type)
                *_, file_extension = file_type.value.split('/')
                if replace_path := image.headers.get('x-origin-path'):
                    path = replace_path
                else:
                    path = f'{self.root}/{product.id}/{start_index}.{file_extension}'
                    start_index += 1
                file_body = await image.read()
                upload_result = await ob_c.put_object_async(path, file_body)
                if upload_result and upload_result.crc:
                    product.images.append(ImageFileType(file_path=path, file_type=file_type))
                else:
                    self.operating_failed(f'{image.filename} upload image failed')
            await product.update_fields(images=product.images)


class GetPaymentCheckoutSessionViewModel(BasePaymentViewModel):
    def __init__(self, session_id: str, payment_gateway: PaymentGatewayEnum, request: Request):
        super().__init__(payment_gateway=payment_gateway, request=request)
        self.session_id = session_id

    async def before(self):
        await self.get_checkout_sessions()

    async def get_checkout_sessions(self):
        async with self.payment_execution() as controller:
            response = await controller.get_checkout_session(self.session_id)
            if not isinstance(response, dict):
                self.operating_failed(response or 'session not exist')
            self.operating_successfully(PaymentCheckoutSessionQueryResponseData(**response))


class CreatePaymentCheckoutSessionViewModel(BaseOssViewModel):

    def __init__(self, form_data: CreatePaymentCheckoutSessionForm, payment_gateway: PaymentGatewayEnum):
        super().__init__(need_auth=False)
        self.payment_gateway = payment_gateway
        self.form_data = form_data

    async def before(self):
        await self.create_checkout_session()

    async def create_checkout_session(self):
        auth, product_list = await self.get_good_information_list()
        async with MLPGTransactionApiController(
                self.payment_gateway,
                auth.authorization.get('publicKey', ''),
                auth.authorization.get('secretKey', '')
        ) as controller:
            response = await self.create_session_with_product_list(controller, product_list)
            if not isinstance(response, dict):
                self.operating_failed(response)
            if not response.get('url'):
                self.operating_failed('checkout session create failed')
            self.operating_successfully(response.get('url', ''))

    async def get_good_information_list(self) -> tuple[
        OrganizationPaymentGatewayConfigurationType, list[TransactionCheckoutSessionLineItemType]
    ]:
        if self.form_data.goods:
            return await self.get_good_information_list_with_predefined_products()
        if not self.form_data.tempGoods:
            self.not_found('goods and tempGoods must be provided at least one')
        return await self.get_good_information_list_with_temporary_products()

    async def get_good_information_list_with_predefined_products(self) -> tuple[
        OrganizationPaymentGatewayConfigurationType, list[
            tuple[CreatePaymentCheckoutSessionGoodType, PaymentProductModel]
        ]]:
        p_id_list = {good.productId for good in self.form_data.goods}
        if not (product_list := await PaymentProductModel.find(
                In(PaymentProductModel.id, [PydanticObjectId(p_id) for p_id in p_id_list])
        ).to_list()):
            self.not_found('payment product not exist')
        if not (org_config := await OrganizationConfigurationModel.find_one(
                OrganizationConfigurationModel.affiliation == product_list[0].affiliation.creator
        )):
            self.not_found('organization not exist')
        if not (pg_config := org_config.get_payment_gateway_configuration(self.payment_gateway)):
            self.not_found('payment gateway not exist')
        product_map = {str(product.id): product for product in product_list}
        return pg_config, [TransactionCheckoutSessionLineItemType(
            name=f'{product.name} - {product.options.get(good.option).name}', description=product.briefDescription,
            images=await self.gen_access_url([image.file_path for image in product.images]),
            unitAmount=product.options.get(good.option).unitAmount, quantity=good.quantity,
        ) for good in self.form_data.goods if (product := product_map.get(good.productId))]

    async def get_good_information_list_with_temporary_products(self) -> tuple[
        OrganizationPaymentGatewayConfigurationType, list[TransactionCheckoutSessionLineItemType]
    ]:
        if not (event := await EventModel.get(self.form_data.tempGoods.eventId)):
            self.not_found('event not exist')
        if not (org_config := await OrganizationConfigurationModel.find_one(
                OrganizationConfigurationModel.affiliation == event.affiliation.creator
        )):
            self.not_found('organization not exist')
        if not (pg_config := org_config.get_payment_gateway_configuration(self.payment_gateway)):
            self.not_found('payment gateway not exist')
        return pg_config, [TransactionCheckoutSessionLineItemType(
            name=self.form_data.tempGoods.name, description=self.form_data.consumer,
            images=await self.gen_access_url([event.background.file_path]),
            unitAmount=self.form_data.tempGoods.unitAmount, quantity=1,
        )]

    async def create_session_with_product_list(
            self, controller: MLPGTransactionApiController, good_list: list[TransactionCheckoutSessionLineItemType]
    ):
        return await controller.create_new_checkout_session(CreateNewCheckoutSessionForm(
            orderId=str(uuid4()), currency='HKD', goodList=good_list, submitType=SubmitTypeEnum.PAY.value,
            paymentMethodTypes=[], successUrl=self.form_data.successUrl.unicode_string(),
            failedUrl=self.form_data.failedUrl.unicode_string()
        ), {'x-pg-referer': get_settings().FRONTEND_DOMAIN, 'x-pg-consumer': self.form_data.consumer})


class PaymentGatewayConfigurationChangeViewModel(BasePaymentViewModel):

    def __init__(self, form_data: PaymentGatewayConfigurationChangeForm, request: Request):
        super().__init__(payment_gateway=form_data.category, request=request)
        self.form_data = form_data

    async def before(self):
        match self.user_title:
            case UserTitleEnum.ADMIN:
                await self.change_admin_payment_gateway_enabled()
            case UserTitleEnum.ORGANIZATION:
                await self.change_organization_payment_gateway_configuration()
        await self.change_admin_payment_gateway_enabled()

    async def change_admin_payment_gateway_enabled(self):
        if not (config := await AdminConfigurationModel.find_one(
                AdminConfigurationModel.affiliation == self.user_email
        )):
            self.not_found('admin configuration not found')
        if not (payment_gateway_category := config.payment_gateway.get(self.form_data.category.value)):
            self.forbidden('payment gateway category not found')
        payment_gateway_category.enable = self.form_data.enabled
        config.payment_gateway.update({self.form_data.category.value: payment_gateway_category})
        await config.update_fields(payment_gateway=config.payment_gateway)
        self.operating_successfully(
            f'{self.form_data.category.name.title()} enabled change to {self.form_data.enabled} successfully'
        )

    async def change_organization_payment_gateway_configuration(self):
        if not (config := await OrganizationConfigurationModel.find_one(
                OrganizationConfigurationModel.affiliation == self.user_email
        )):
            self.not_found('organization configuration not found')
        if not (payment_gateway_category := config.payment_gateway.get(self.form_data.category.value)):
            self.forbidden('payment gateway category not found')
        if self.form_data.enabled is not None:
            payment_gateway_category.enable = self.form_data.enabled
        if self.form_data.env is not None:
            if self.form_data.authorization:
                authorization, methods = await self.get_target_payment_gateway_methods()
                payment_gateway_category.configuration.update({
                    self.form_data.env.value: OrganizationPaymentGatewayConfigurationType(
                        methods=methods, authorization=authorization
                    )}
                )
            elif self.form_data.env.value not in payment_gateway_category.configuration:
                self.forbidden('payment gateway configuration of target env not found')
            payment_gateway_category.env = self.form_data.env
        config.payment_gateway.update({self.form_data.category.value: payment_gateway_category})
        await config.update_fields(payment_gateway=config.payment_gateway)
        self.operating_successfully(f'{self.form_data.category.name.title()} configuration change successfully')

    async def get_target_payment_gateway_methods(self) -> tuple[dict, list[dict]]:
        p_key, s_key, authorization = await self.get_payment_gateway_authorization(
            self.form_data.category, self.form_data.authorization
        )
        async with MLPGTransactionApiController(self.form_data.category, p_key, s_key) as mlpg_api:
            if not (payment_method_data := await mlpg_api.get_payment_method_list(available=True)):
                self.forbidden('payment gateway authorization failed')
            return authorization, payment_method_data.get('methods', [])


# class GetPaymentLinkViewModel(BasePaymentViewModel):
#     def __init__(self, email: str):
#         super().__init__(need_auth=False)
#         self.email = email
#
#     async def before(self):
#         await self.get_payment_links()
#
#     async def get_payment_links(self):
#         pass
#
#
# class CreatePaymentLinkViewModel(BasePaymentViewModel):
#     def __init__(self, email: str):
#         super().__init__(need_auth=False)
#         self.email = email
#
#     async def before(self):
#         await self.create_payment_link()
#
#     async def create_payment_link(self):
#         pass

class GetPaymentMethodViewModel(BasePaymentViewModel):
    def __init__(self, payment_gateway: PaymentGatewayEnum, event_id: str, request: Request = None):
        super().__init__(payment_gateway=payment_gateway, request=request)

    async def before(self):
        await self.get_payment_methods()

    async def get_payment_methods(self):
        async with self.payment_execution() as controller:
            method_info = await controller.get_payment_method_list(available=True)
            method_list = method_info.get('methods')
            if not isinstance(method_list, list):
                self.operating_failed(method_info)
            self.operating_successfully([PaymentMethodQueryResponseDataItem(
                key=method.get('key', ''), name=method.get('name', ''),
                available=method.get('available', bool), gateway=self.payment_gateway
            ) for method in method_list])

# class GetStripePaymentPriceViewModel(BaseViewModel):
#     def __init__(self, request: Request):
#         super().__init__(request=request, access_title=[UserTitleEnum.ORGANIZATION])
#         self.payment_gateway = PaymentGatewayEnum.STRIPE
#
#     async def before(self):
#         await super().before()
#         await self.get_stripe_price()
#
#     async def get_stripe_price(self):
#         if not (pg_config := self.user_instance.payment_gateway.get(self.payment_gateway.value)):
#             self.forbidden('payment gateway not exist, please config it first')
#         p_k, s_k = pg_config.get('public_key'), pg_config.get('secret_key')
#         async with MLPGStripeApiController(p_k, s_k) as mlpg_api:
#             price_response = await mlpg_api.get_price(GetStripePriceForm())
#             if not isinstance(price_response, list):
#                 self.operating_failed(price_response)
#             self.operating_successfully([{
#                 'id': price.get('id'), 'unitAmount': price.get('unit_amount'), 'currency': price.get('currency'),
#                 'type': price.get('type'),
#             } for price in price_response])
#
#
# class CreateStripePaymentPriceViewModel(BasePaymentViewModel):
#     def __init__(self, request: Request):
#         super().__init__(payment_gateway=PaymentGatewayEnum.STRIPE, request=request)
#
#     async def before(self):
#         await self.create_new_price()
#
#     async def create_new_price(self):
#         admin = await UserModel.find_one(UserModel.title == UserTitleEnum.ADMIN)
