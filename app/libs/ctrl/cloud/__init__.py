import abc
import socket
import uuid

from app.libs.ctrl import BaseDataProcess

__all__ = (
    'BaseCloudProviderController',
    'AzureBlobController',
    'AzureBlobUploadResult',
)


class BaseCloudProviderController(BaseDataProcess):

    def __init__(self, result: list | dict = None):
        super().__init__(result or [], f'{self.cls_name()}.csv', f'{self.cls_name()}.json')

    @abc.abstractmethod
    def login(self):
        pass

    @property
    def uuid(self):
        name = socket.gethostname() + str(uuid.uuid1())
        namespace = uuid.NAMESPACE_URL
        return str(uuid.uuid5(namespace, name))


from .azure import *
from .ali import *
