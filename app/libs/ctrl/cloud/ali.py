import abc
import base64
import math
from typing import List

import alibabacloud_alb20200616.models as alb_models
from Tea.exceptions import TeaException
from alibabacloud_agency20221216 import models as agency_models
from alibabacloud_agency20221216.client import Client as AgencyClient
from alibabacloud_agency20221216.models import GetAccountInfoResponseBodyAccountInfoListAccountInfo
from alibabacloud_alb20200616.client import Client as AlbClient
from alibabacloud_bssopenapi20171214 import models as bss_models
# from alibabacloud_ram20150501 import models as ram_models
# from alibabacloud_sts20150401 import models as sts_models
from alibabacloud_bssopenapi20171214.client import Client as BssOpenApiClient
from alibabacloud_ram20150501 import models as ram_models
from alibabacloud_ram20150501.client import Client as RamClient
from alibabacloud_sts20150401.client import Client as StsClient
from alibabacloud_tea_openapi.models import Config
from alibabacloud_tea_util.models import RuntimeOptions
from aliyunsdkcore.acs_exception.exceptions import ClientException
from oss2 import Bucket, Auth, CaseInsensitiveDict, models as oss_models
from oss2.exceptions import NoSuchKey
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.libs.ctrl.cloud import BaseCloudProviderController
from app.models import SupportImageMIMEType, SupportDataMIMEType

# 使用环境变量中获取的RAM用户的访问密钥配置访问凭证。
__all__ = (
    'AliCloudOssBucketController',
)

from app.models.events import EventModel, DomainModeEnum


class BaseAliCloudProviderController(BaseCloudProviderController):
    def __init__(self, access_key: str, access_secret: str, region_id: str, result: list | dict):
        super().__init__(result or [])
        self._access_key = access_key
        self._access_secret = access_secret
        self._region_id = region_id
        self._page_no = 1
        self._page_size = 300  # max page size is 300

    @abc.abstractmethod
    def login(self):
        pass

    @property
    def options(self) -> RuntimeOptions:
        return RuntimeOptions(
            autoretry=True, ignore_ssl=True
        )


class AliCloudBillController(BaseAliCloudProviderController, BssOpenApiClient):
    FORMAT_ISO_8601 = "%Y-%m-%dT%H:%M:%SZ"

    def __init__(self, access_key: str, access_secret: str, region_id: str, result: list | dict = None):
        BaseAliCloudProviderController.__init__(self, access_key, access_secret, region_id, result)
        # if region_id == 'ap-southeast-1':
        #     self.endpoint = 'business.ap-southeast-1.aliyuncs.com'
        # else:
        #     self.endpoint = 'business.aliyuncs.com'

    async def login(self):
        config = Config(
            access_key_id=self._access_key,
            access_key_secret=self._access_secret,
            # Endpoint 请参考 https://api.aliyun.com/product/Agency
            endpoint='business.ap-southeast-1.aliyuncs.com',
            # region_id=self._region_id
        )
        BssOpenApiClient.__init__(self, config)

    def set_page_no(self, page_no: int):
        self._page_no = page_no

    def set_page_size(self, page_size: int):
        self._page_size = page_size
        return self

    @property
    def bill_item_list(self) -> List[dict]:
        return self.result.get('Items', {}) if isinstance(self.result, dict) else self.result

    async def get_client_list(self) -> list[str, ...]:
        response: bss_models.GetCustomerListResponse = await self.get_customer_list_with_options_async(self.options)
        body = response.body
        print(f'client response {response.to_map()}')
        if not body.success or not body.data:
            return []
        return body.data.uid_list

    async def get_client_info(self, client_id: str) -> dict:
        request = bss_models.GetCustomerAccountInfoRequest(client_id)
        response = await self.get_customer_account_info_with_options_async(
            request, self.options
        )
        body = response.body
        if not body.success:
            return {}
        return {**body.data.to_map(), 'clientId': int(client_id)}

    async def get_account_balance(self) -> bss_models.QueryAccountBalanceResponseBodyData:
        try:
            response = await self.query_account_balance_with_options_async(
                self.options
            )
            body = response.body
            if not body.success:
                return {}
            return body.data
        except TeaException as e:
            print('client exception: ', e)
            return e.code
            # return 'error'
        # response = await self.query_account_balance_with_options_async(
        #     self.options
        # )
        # print('response: ', response)
        # body = response.body
        # print('account balance: ', body)
        # if not body.success:
        #     return {}
        # return body.data

    async def get_reseller_discount(self):
        request = bss_models.QuerySavingsPlansDiscountRequest(
            pay_mode='total', spn_type='universal', cycle='1:Year', commodity_code='ecs'
        )
        response = await self.query_savings_plans_discount_with_options_async(
            request, self.options
        )
        body = response.body
        if not body.success:
            return {}
        return body.data

    async def get_overview_bill(
            self, cycle: str, account_id: int | str = ''
    ) -> list[bss_models.QueryBillOverviewResponseBodyDataItemsItem]:
        request = bss_models.QueryBillOverviewRequest(
            billing_cycle=cycle
        )
        if account_id:
            request.bill_owner_id = int(account_id)
        response = await self.query_bill_overview_with_options_async(
            request, self.options
        )
        body = response.body
        if not body.success:
            return []
        return body.data.items.item

    async def get_daily_overview_bill(
            self, cycle: str, account_id: int | str = '', page_no: int = 1
    ) -> list[bss_models.QueryBillOverviewResponseBodyDataItemsItem]:
        year, month, day = cycle.split('-')
        request = bss_models.QueryAccountBillRequest(
            billing_cycle=f'{year}-{month}', billing_date=f'{year}-{month}-{day}',
            granularity='DAILY', page_num=page_no, page_size=300
        )
        if account_id:
            request.owner_id = int(account_id)
            # request.bill_owner_id = int(account_id)
        response = await self.query_account_bill_with_options_async(
            request, self.options
        )
        body = response.body
        if not body.success:
            return []
        data = body.data
        if data.total_count > data.page_size * data.page_num:
            return data.items.item + await self.get_daily_overview_bill(cycle, account_id, page_no=data.page_num + 1)
        return body.data.items.item

    async def fetch_full_bills_from_provider(
            self, billing_cycle: str, account_id: str = '', page_no: int = 1, page_size: int = 100
    ):
        data = await self.fetch_bills_from_provider(billing_cycle, account_id, page_no, page_size)
        if not self.result:
            self.result = {**data.to_map(), 'Items': data.items.to_map().get('Item', [])}
        else:
            self.result.get('Items', []).extend(data.items.to_map().get('Item', []))
        if data.total_count > data.page_num * data.page_size:
            await self.fetch_full_bills_from_provider(billing_cycle, account_id, data.page_num + 1, data.page_size)

    async def fetch_bills_from_provider(
            self, billing_cycle: str, account_id: str = '', page_no: int = 1, page_size: int = 100
    ) -> bss_models.QueryBillResponseBodyData:
        request = bss_models.QueryBillRequest(
            bill_owner_id=account_id, billing_cycle=billing_cycle, page_num=page_no, page_size=page_size
        )
        response = await self.query_bill_with_options_async(request, self.options)
        body = response.body
        if not body.success:
            return []
        return body.data

    async def fetch_aggregation_bills(self, billing_cycle: str, account_id: str = '', next_token: str = ''):
        """
        fetch aggregation bill list
        If the billing_cycle is accurate to the day, the granularity will be DAILY (query daily bills)
        or it will be MONTHLY (query monthly bills)
        @param billing_cycle: Support accuracy in months or days
        @param account_id: bill owner id
        @param next_token: sdk function pagination token, only for recursion use, No need to explicitly pass in
        @return: None, use ctrl instance's result property to get the bill result
        """
        request_body = {
            'bill_owner_id': account_id, 'billing_cycle': billing_cycle,
            'next_token': next_token, 'max_results': self._page_size
        }
        if len((date_seg := billing_cycle.split('-'))) > 2:
            year, month, _ = date_seg
            request_body.update(granularity='DAILY', billing_cycle=f'{year}-{month}', billing_date=billing_cycle)
        request = bss_models.DescribeInstanceBillRequest(**request_body)
        response: bss_models.DescribeInstanceBillResponse = await self.describe_instance_bill_with_options_async(
            request, self.options
        )
        body: bss_models.DescribeInstanceBillResponseBody = response.body
        data: bss_models.DescribeInstanceBillResponseBodyData = body.data
        if not body.success:
            return []
        if not self.result:
            self.result = data.to_map()
        else:
            self.result.get('items', []).extend(data.to_map().get('items', []))
        if data.next_token:
            await self.fetch_aggregation_bills(billing_cycle, account_id, data.next_token)

    async def fetch_product_list(self):
        """
        @return: None, use ctrl instance's result property to get the product list
        """
        request = bss_models.QueryProductListRequest(
            query_total_count=True, page_num=self._page_no, page_size=self._page_size
        )
        response: bss_models.QueryProductListResponse = await self.query_product_list_with_options_async(
            request, self.options
        )
        body: bss_models.QueryProductListResponseBody = response.body
        if not body.success:
            return {}
        if not self.result:
            self.result: list = body.data.product_list.product
        else:
            self.result.extend(body.data.product_list.product)
        if body.data.total_count > self._page_no * self._page_size:
            self._page_no += 1
            await self.fetch_product_list()

    @staticmethod
    def calc_sum_of_bill_fields(
            bill_list: list[bss_models.QueryBillOverviewResponseBodyDataItemsItem], field_list: List[str]
    ):
        if bill_list:
            res = []
            for field in field_list:
                res.append(math.fsum([
                    float(item_dict.get(field, 0)) for item in bill_list if (item_dict := item.to_map())
                ]))
            return res
        return [0 for _ in field_list]

    def calc_sum_of_bill_fields_with_sdk_bills(self, field_list: List[str]):
        return [math.fsum(
            [float(item.get(field, 0)) for item in self.bill_item_list]
        ) for field in field_list] if self.bill_item_list else [0 for _ in field_list]


class AliCloudCreditController(BaseAliCloudProviderController, AgencyClient):
    FORMAT_ISO_8601 = "%Y-%m-%dT%H:%M:%SZ"

    def __init__(self, access_key: str, access_secret: str, region_id: str, result: list | dict = None):
        BaseAliCloudProviderController.__init__(self, access_key, access_secret, region_id, result or [])

    async def login(self):
        config = Config(
            access_key_id=self._access_key,
            access_key_secret=self._access_secret,
            # Endpoint 请参考 https://api.aliyun.com/product/Agency
            # region_id=self._region_id
            endpoint='agency.ap-southeast-1.aliyuncs.com'
        )
        AgencyClient.__init__(self, config)

    async def set_client_credit(self, client_id: str, credit_line: int) -> str:
        request = agency_models.SetCreditLineRequest(str(credit_line), int(client_id))
        response: agency_models.SetCreditLineResponse = await self.set_credit_line_with_options_async(
            request, self.options
        )
        body: agency_models.SetCreditLineResponseBody = response.body
        if not body.success:
            raise ClientException(f'Request ID: {body.request_id}: {body.message}')
        return body.message

    async def get_client_info(self, client_id: str) -> dict:
        self._page_size = 20
        request = agency_models.GetAccountInfoRequest(
            current_page=self._page_no, page_size=self._page_size, uid=client_id
        )
        response: agency_models.GetAccountInfoResponse = await self.get_account_info_with_options_async(
            request, self.options
        )
        body: agency_models.GetAccountInfoResponseBody = response.body
        if not body.success:
            return {}
        account_info = body.account_info_list.account_info
        return {**account_info[0].to_map(), 'clientId': int(client_id)} if account_info else {}

    async def get_client_info_list(
            self, client_id: str | int = '', user_type: str = '', page_no: int = 1, page_size: int = 20
    ) -> list[GetAccountInfoResponseBodyAccountInfoListAccountInfo]:
        query_condition = {'current_page': page_no, 'page_size': page_size}
        if client_id:
            query_condition.update(uid=int(client_id))
        else:
            query_condition.update(user_type=user_type or '1')
        request = agency_models.GetAccountInfoRequest(**query_condition)
        response: agency_models.GetAccountInfoResponse = await self.get_account_info_with_options_async(
            request, self.options
        )
        body: agency_models.GetAccountInfoResponseBody = response.body
        if not body.success:
            return []
        [print(
            f'UID: {client_info.uid}, NickName: {client_info.account_nickname}, Email: {client_info.email}, Remark: {client_info.remark}'
        ) for client_info in body.account_info_list.account_info]
        if body.page_info.page * body.page_info.page_size < body.page_info.total:
            return [*body.account_info_list.account_info, *(
                await self.get_client_info_list(client_id, user_type, page_no + 1, page_size)
            )]
        else:
            return body.account_info_list.account_info

    async def get_client_credit_info(self, client_id: str) -> agency_models.GetCreditInfoResponseBodyData:
        request = agency_models.GetCreditInfoRequest(client_id)
        response: agency_models.GetCreditInfoResponse = await self.get_credit_info_with_options_async(
            request, self.options
        )
        return response.body.data


class AliCloudRAMController(BaseAliCloudProviderController, RamClient):

    def __init__(self, access_key: str, access_secret: str, region_id: str, result: list | dict = None):
        BaseAliCloudProviderController.__init__(self, access_key, access_secret, region_id, result or [])

    async def login(self):
        config = Config(
            access_key_id=self._access_key,
            access_key_secret=self._access_secret,
            # Endpoint 请参考 https://api.aliyun.com/product/Agency
            region_id=self._region_id
        )
        RamClient.__init__(self, config)

    async def get_policy_list(self):
        request = ram_models.ListPoliciesRequest()
        response = await self.list_policies_with_options_async(request, self.options)
        print((response.to_map()))
        return response.body

    async def validate_account_id(self, account_id: str):
        try:
            request = ram_models.GetUserRequest()
            response = await self.get_user_with_options_async(request, self.options)
            print(response.body)
        except TeaException as e:
            print(e)


class AliCloudSTSController(BaseAliCloudProviderController, StsClient):

    def __init__(self, access_key: str, access_secret: str, region_id: str, result: list | dict = None):
        BaseAliCloudProviderController.__init__(self, access_key, access_secret, region_id, result or [])

    async def login(self):
        config = Config(
            access_key_id=self._access_key,
            access_key_secret=self._access_secret,
            # Endpoint 请参考 https://api.aliyun.com/product/Agency
            region_id=self._region_id
        )
        StsClient.__init__(self, config)

    async def validate_account_id(self, account_id: str):
        try:
            response = await self.get_caller_identity_async()
            # response = await self.get_caller_identity_with_options_async( self.options)
            if response.body.account_id == account_id:
                return response.body
            return -1
        except TeaException as e:
            print(e)
            return -1


class AliCloudOssBucketController(BaseAliCloudProviderController, Bucket):

    def __init__(self, result: list | dict = None):
        BaseAliCloudProviderController.__init__(
            self, access_key=get_settings().ALI_OSS_ACCESS_KEY, access_secret=get_settings().ALI_OSS_ACCESS_SECRET,
            region_id=get_settings().ALI_OSS_REGION, result=result
        )
        self.bucket_name = get_settings().ALI_OSS_BUCKET_NAME

    @property
    def access_url_prefix(self) -> str:
        return f'https://{self.bucket_name}.oss-{self._region_id}.aliyuncs.com/'

    async def login(self):
        auth = Auth(
            access_key_id=self._access_key,
            access_key_secret=self._access_secret,
        )
        Bucket.__init__(
            self, auth=auth, bucket_name=self.bucket_name,
            endpoint=f'oss-{self._region_id}.aliyuncs.com', region=self._region_id
        )

    async def get_bucket_info_async(self) -> oss_models.GetBucketInfoResult:
        result: oss_models.GetBucketInfoResult = await run_in_threadpool(self.get_bucket_info)
        return result if result.status == 200 else None

    async def put_object_with_public_read_async(self, file_path: str, body: bytes) -> oss_models.PutObjectResult:
        return await self.put_object_async(file_path, body, headers={'x-oss-object-acl': 'public-read'})

    async def put_object_async(self, file_path: str, body: bytes, headers: dict = None) -> oss_models.PutObjectResult:
        request_headers = CaseInsensitiveDict()
        request_headers.setdefault('Content-Disposition', 'inline')
        if headers:
            request_headers.update(headers)
        result = await run_in_threadpool(self.put_object, key=file_path, data=body, headers=request_headers)
        return result if result.status == 200 else None

    async def get_object_async(self, file_path: str, headers: dict = None) -> oss_models.GetObjectResult:
        request_headers = CaseInsensitiveDict()
        request_headers.setdefault('response-content-disposition', 'inline')
        if headers:
            request_headers |= headers
        result = await run_in_threadpool(self.get_object, key=file_path, headers=request_headers)
        return result if result.status == 200 else None

    async def get_object_with_base64_async(
            self, file_path: str, file_type: (SupportImageMIMEType | SupportDataMIMEType)
    ) -> str:
        try:
            if not file_path:
                return f'data:{file_type.value};base64,'
            avatar_type = SupportImageMIMEType.check_value_exists(file_type.value)
            if all([not avatar_type]):
                return ''
            result: oss_models.GetObjectResult = await run_in_threadpool(self.get_object, key=file_path)
            file_object = result.stream.read()
            # 将PDF字节内容编码为Base64字符串
            pdf_base64 = base64.b64encode(file_object)
            # 将字节对象转换为字符串（如果需要）
            pdf_base64_str = pdf_base64.decode('utf-8')
            return f'data:{file_type.value};base64,{pdf_base64_str}'
        except NoSuchKey:
            return f'data:{file_type.value};base64,'

    async def generate_object_access_url_async(self, file_path: str, expire: int = 60):
        signed_url = await run_in_threadpool(self.sign_url, method='GET', key=file_path, expires=expire)
        return signed_url


class AliCloudALBController(BaseAliCloudProviderController, AlbClient):

    def __init__(self, access_key: str, access_secret: str, region_id: str, result: list | dict = None):
        BaseAliCloudProviderController.__init__(self, access_key, access_secret, region_id, result)

    async def login(self):
        config = Config(
            access_key_id=self._access_key,
            access_key_secret=self._access_secret,
            # Endpoint 请参考 https://api.aliyun.com/product/Agency
            endpoint='alb.cn-hongkong.aliyuncs.com', region_id=self._region_id
        )
        AlbClient.__init__(self, config)

    async def add_event_listener(self, event: EventModel, event_domain: str) -> bool:
        if not await self.query_alb_instance():
            return False
        if not await self.query_alb_http_listener():
            return False
        return await self.set_event_listener_rule(event, event_domain)

    async def query_alb_instance(self):
        request = alb_models.GetLoadBalancerAttributeRequest(
            load_balancer_id=get_settings().ALI_LUMIO_ALB_ID
        )
        response = await self.get_load_balancer_attribute_with_options_async(request, self.options)
        if response.status_code != 200:
            return None
        return response.body

    async def query_alb_http_listener(self):
        request = alb_models.GetListenerAttributeRequest(listener_id=get_settings().ALI_LUMIO_ALB_LISTENER_ID)
        response = await self.get_listener_attribute_with_options_async(request, self.options)
        if response.status_code != 200:
            return None
        return response.body

    async def set_event_listener_rule(self, event: EventModel, event_domain: str):
        rule_name = f'{event.name.lower().replace(" ", "-")}-{event.sid}-rule'
        if event.domainSettings.domainMode == DomainModeEnum.NONE:
            return await self.add_event_listener_rule(event, event_domain, rule_name)
        return await self.update_event_listener_rule(event, event_domain)

    async def add_event_listener_rule(self, event: EventModel, event_domain: str, rule_name: str):
        exists_rule_count = await self.get_listener_rule_count()
        request = alb_models.CreateRuleRequest(
            listener_id=get_settings().ALI_LUMIO_ALB_LISTENER_ID,
            priority=exists_rule_count + 1, rule_name=rule_name
        )
        request.rule_conditions = self.generate_rule_conditions(event_domain)
        request.rule_actions = self.generate_rule_actions(event)
        request.tag = [alb_models.CreateRuleRequestTag(key='Lumio Event Listener Rule', value=event.sid)]
        response = await self.create_rule_with_options_async(request, self.options)
        if response.status_code != 200:
            return False
        domain_settings = event.domainSettings
        domain_settings.domainMode = DomainModeEnum.CUSTOM
        *sub_domain, domain_name, area = event_domain.split('.')
        domain_settings.domain = f'{domain_name}.{area}'
        domain_settings.subDomain = '.'.join(sub_domain) or 'www'
        domain_settings.ruleId = response.body.rule_id
        await event.update_fields(domainSettings=domain_settings)
        return True

    async def update_event_listener_rule(self, event: EventModel, event_domain: str):
        pass

    async def get_listener_rule_count(self) -> int:
        request = alb_models.ListRulesRequest(listener_ids=[get_settings().ALI_LUMIO_ALB_LISTENER_ID])
        response = await self.list_rules_with_options_async(request, self.options)
        if response.status_code != 200:
            return 0
        return response.body.total_count

    @staticmethod
    def generate_rule_conditions(event_domain: str) -> list[
        alb_models.CreateRuleRequestRuleConditions
    ]:
        return [
            alb_models.CreateRuleRequestRuleConditions(
                type='Host', host_config=alb_models.CreateRuleRequestRuleConditionsHostConfig([event_domain])
            ),
            alb_models.CreateRuleRequestRuleConditions(
                type='Path', path_config=alb_models.CreateRuleRequestRuleConditionsPathConfig(['/*'])
            )
        ]

    @staticmethod
    def generate_rule_actions(event: EventModel) -> list[
        alb_models.CreateRuleRequestRuleActions
    ]:
        return [
            alb_models.CreateRuleRequestRuleActions(
                order=1, type='Rewrite', rewrite_config=alb_models.CreateRuleRequestRuleActionsRewriteConfig(
                    path=f'/{event.sid}/en${{path}}', query='${query}', host='${host}'
                )
            ),
            alb_models.CreateRuleRequestRuleActions(
                order=2, type='ForwardGroup',
                forward_group_config=alb_models.CreateRulesRequestRulesRuleActionsForwardGroupConfig(
                    server_group_tuples=[
                        alb_models.CreateRulesRequestRulesRuleActionsForwardGroupConfigServerGroupTuples(
                            server_group_id=get_settings().ALI_LUMIO_ALB_EVENT_BACKEND_SERVER_GROUP_ID
                        )
                    ]
                )
            )
        ]
