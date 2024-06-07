import abc
import base64

from oss2 import Bucket, Auth, CaseInsensitiveDict
from oss2 import models as oss_models
from starlette.concurrency import run_in_threadpool

from app.libs.controller.cloud_provider import BaseCloudProviderController
from app.models.user import SupportCertificateMIMEType

# 使用环境变量中获取的RAM用户的访问密钥配置访问凭证。
__all__ = (
    'AliCloudOssBucketController',
)


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


class AliCloudOssBucketController(BaseAliCloudProviderController, Bucket):

    def __init__(
            self, access_key: str, access_secret: str, region_id: str, bucket_name: str, result: list | dict = None
    ):
        BaseAliCloudProviderController.__init__(self, access_key, access_secret, region_id, result)
        self.bucket_name = bucket_name

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

    async def put_object_async(self, file_path: str, body: bytes) -> oss_models.PutObjectResult:
        headers = CaseInsensitiveDict()
        headers.setdefault('Content-Disposition', 'inline')
        result = await run_in_threadpool(self.put_object, key=file_path, data=body, headers=headers)
        return result if result.status == 200 else None

    async def get_object_with_base64_async(self, file_path: str, file_type: SupportCertificateMIMEType) -> str:
        if not (b64_header := {
            SupportCertificateMIMEType.APPLICATION_PDF: 'data:application/pdf;base64,',
            SupportCertificateMIMEType.IMAGE_PNG: 'data:image/png;base64,',
            SupportCertificateMIMEType.IMAGE_JPG: 'data:image/jpg;base64,',
            SupportCertificateMIMEType.IMAGE_JPEG: 'data:image/jpeg;base64,'
        }.get(file_type)):
            return None
        result: oss_models.GetObjectResult = await run_in_threadpool(self.get_object, key=file_path)
        file_object = result.stream.read()
        # 将PDF字节内容编码为Base64字符串
        pdf_base64 = base64.b64encode(file_object)
        # 将字节对象转换为字符串（如果需要）
        pdf_base64_str = pdf_base64.decode('utf-8')
        return f'{b64_header}{pdf_base64_str}'

    async def generate_object_access_url_async(self, file_path: str, expire: int = 60):
        signed_url = await run_in_threadpool(self.sign_url, method='GET', key=file_path, expires=expire)
        return signed_url
