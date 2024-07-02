import abc
import math
from typing import List

from alibabacloud_agency20221216 import models as agency_models
from alibabacloud_agency20221216.client import Client as AgencyClient
from alibabacloud_bssopenapi20171214 import models as bss_models
from alibabacloud_bssopenapi20171214.client import Client as BssOpenApiClient
from alibabacloud_tea_openapi.models import TeaModel, Config
from alibabacloud_tea_util.models import RuntimeOptions
from aliyunsdkcore.acs_exception.exceptions import ClientException

from app.libs.cloud_provider import BaseCloudProviderController

__all__ = (
    'AliCloudBillController',
    'AliCloudResponseBody',
    'AliCloudCreditController',
)


class AliCloudResponseBody(TeaModel):
    def __init__(
            self,
            code: str = None,
            message: str = None,
            request_id: str = None,
            success: bool = None,
    ):
        super().__init__()
        self.code = code
        self.message = message
        self.request_id = request_id
        self.success = success

    def validate(self):
        pass


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

    async def login(self):
        config = Config(
            access_key_id=self._access_key,
            access_key_secret=self._access_secret,
            # Endpoint 请参考 https://api.aliyun.com/product/Agency
            endpoint='business.ap-southeast-1.aliyuncs.com'
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
        if not body.success:
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
        response = await self.query_account_balance_with_options_async(
            self.options
        )
        body = response.body
        if not body.success:
            return {}
        return body.data

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
        @return: None, use controller instance's result property to get the bill result
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
        @return: None, use controller instance's result property to get the product list
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

    async def get_client_credit_info(self, client_id: str) -> agency_models.GetCreditInfoResponseBodyData:
        request = agency_models.GetCreditInfoRequest(client_id)
        response: agency_models.GetCreditInfoResponse = await self.get_credit_info_with_options_async(
            request, self.options
        )
        return response.body.data
