from fastapi import Request

from app.forms.account import *
from app.libs.mlpg_api_controller import PaymentGatewayEnum
from app.models.account import UserTitleEnum, UserStatusEnum, AdminPaymentGatewayType
from app.models.account.admin import AdminConfigurationModel
from app.models.common import UserModel
from app.models.account.organization import OrganizationCertificationModel
from app.view_models import BaseViewModel, BaseOssViewModel, BaseAccountAvatarOssViewModel

__all__ = (
    'GetAdminListViewModel',
    'GetAdminConfigurationViewModel',
    'GetApprovalAccountViewModel',
    'ExecuteApprovalAccountViewModel',
)


class GetAdminListViewModel(BaseAccountAvatarOssViewModel):
    def __init__(self):
        super().__init__(need_auth=False)

    async def before(self):
        admin_list = await UserModel.find(UserModel.title == UserTitleEnum.ADMIN).to_list()
        self.operating_successfully([
            admin.information | {'avatar': await self.gen_access_url(admin.avatar.file_path)} for admin in admin_list
        ])


class GetAdminConfigurationViewModel(BaseOssViewModel):

    def __init__(self, request: Request):
        super().__init__(request, access_title=[UserTitleEnum.ADMIN])
        self.root = 'payment_gateway'

    async def before(self):
        await self.get_admin_configuration()

    async def get_admin_configuration(self):
        if not (config := await AdminConfigurationModel.find_one(
                AdminConfigurationModel.affiliation == self.user_email
        )):
            config = await AdminConfigurationModel.insert_one(AdminConfigurationModel(
                affiliation=self.user_email,
                payment_gateway={category.value: AdminPaymentGatewayType(
                    name=category.name.title(),
                    image=f'{self.root}/logo/{category.value}.png',
                    enable=True
                ) for category in PaymentGatewayEnum}
            ))
        self.operating_successfully(config.information | {'payment_gateway': {key: val.model_dump() | {
            'image': await self.gen_access_url(file_path=val.image)
        } for key, val in config.payment_gateway.items()}})


class GetApprovalAccountViewModel(BaseAccountAvatarOssViewModel):

    def __init__(self, request: Request):
        super().__init__(request, access_title=[UserTitleEnum.ADMIN])

    async def before(self):
        await self.get_account_register_request()

    async def get_account_register_request(self):
        self.operating_successfully([user.information for user in await UserModel.find(
            UserModel.affiliation == self.user_email, UserModel.proven == False
        ).to_list()])


class ExecuteApprovalAccountViewModel(BaseViewModel):

    def __init__(self, form_data: ApproveAccountForm, request: Request):
        super().__init__(request, access_title=[UserTitleEnum.ADMIN])
        self.form_data = form_data

    async def before(self):
        await self.approve_account()

    async def approve_account(self):
        email = self.form_data.email.lower()
        org_user = await UserModel.find_one(UserModel.email == email, UserModel.affiliation == self.user_email)
        if org_user:
            self.forbidden('organization account can only approve by their affiliation')
        if not (certification := await OrganizationCertificationModel.find_one(
                OrganizationCertificationModel.affiliation == email
        )):
            self.not_found('organization account certification not found')
        if not certification.in_place:
            self.forbidden(
                'organization account certification are not in place (missing any certificate or any certificates are invalid)'
            )
        await org_user.update_fields(proven=True, status=UserStatusEnum.ACTIVE)
        self.operating_successfully(f'{email}  successfully')
