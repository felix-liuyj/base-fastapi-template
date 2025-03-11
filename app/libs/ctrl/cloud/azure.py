import abc
from datetime import datetime, timedelta
from typing import Union

from azure.core.exceptions import AzureError
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from pydantic import BaseModel

from app.config import get_settings  # 假设有一个 settings 文件
from app.libs.ctrl.cloud import BaseCloudProviderController

__all__ = (
    'AzureBlobController',
    'AzureBlobUploadResult',
)


class AzureBlobUploadResult(BaseModel):
    etag: str
    content_md5: str


class BaseAzureProviderController(BaseCloudProviderController):
    def __init__(self, result: list | dict):
        """
        初始化 Azure 云服务控制器。
        :param result: 初始的结果存储，支持列表或字典。
        """
        super().__init__(result or [])
        self.account_name = get_settings().AZURE_BLOB_ACCOUNT_NAME
        self.access_token = get_settings().AZURE_BLOB_ACCESS_TOKEN
        self.container_name = get_settings().AZURE_BLOB_CONTAINER_NAME

    @abc.abstractmethod
    async def login(self):
        """
        登录方法，用于具体的 Azure 服务初始化。
        必须在子类中实现。
        """
        pass


class AzureBlobController(BaseAzureProviderController, BlobServiceClient):
    def __init__(self, result: Union[list, dict] = None):
        # 初始化基类
        BaseAzureProviderController.__init__(self, result=result)
        self.container_client: ContainerClient = None

    @property
    def access_url_prefix(self) -> str:
        """返回 Blob 容器的访问前缀 URL。"""
        return f'https://{self.account_name}.blob.core.windows.net/{self.container_name}'

    async def __aenter__(self):
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.container_client.close()
        await self.close()

    async def login(self):
        """登录并初始化容器客户端。"""
        try:
            # 检查容器是否存在
            # 调用 BlobServiceClient 初始化
            BlobServiceClient.__init__(
                self, f'https://{self.account_name}.blob.core.windows.net', credential=self.access_token
            )
            self.container_client = self.get_container_client(self.container_name)
            await self.container_client.get_container_properties()
            print(f'Connected to container: {self.container_name}')
        except AzureError as e:
            raise ConnectionError(f'Failed to connect to Azure Blob container: {e}')

    async def upload_file(self, file_path: str, data: bytes | str, overwrite: bool = True) -> AzureBlobUploadResult:
        """
        上传 Blob 文件到指定容器的多级路径下。
        :param file_path: 包含路径结构的 Blob 名称（例如 '/folder/subfolder/file.jpg'）。
        :param data: 上传的数据，可以是字节或本地文件路径。
        :param overwrite: 是否覆盖源文件，默认为 True。
        :return:
        """
        try:
            blob_client = self.container_client.get_blob_client(file_path)
            upload_result = await blob_client.upload_blob(data, overwrite=overwrite)
            return AzureBlobUploadResult(
                etag=upload_result.get('etag', ''),
                content_md5=str(upload_result.get('content_md5', ''))
            )
        except AzureError as e:
            raise RuntimeError(f'Failed to upload blob "{file_path}": {e}')

    async def delete_file(self, file_path: str) -> bool:
        """
        上传 Blob 文件到指定容器的多级路径下。
        :param file_path: 包含路径结构的 Blob 名称（例如 '/folder/subfolder/file.jpg'）。
        :return:
        """
        try:
            blob_client = self.container_client.get_blob_client(file_path)
            await blob_client.delete_blob()
            return True
        except AzureError:
            return False
        finally:
            return True

    def generate_access_url(self, blob_name) -> str:
        return f'{self.access_url_prefix}/{blob_name}'

    def generate_sas_url(self, blob_name) -> str:
        sas_token = generate_blob_sas(
            account_name=self.account_name,
            account_key=self.access_token,
            container_name=self.container_name,
            blob_name=blob_name,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now() + timedelta(hours=1)  # 1 小时有效
        )
        return f'{self.access_url_prefix}/{blob_name}?{sas_token}'
