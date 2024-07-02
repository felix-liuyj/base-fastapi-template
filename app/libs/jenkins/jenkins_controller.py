"""
使用 mongoengine 引擎, 以 ODM 的方式将获取到的数据存储到 mongodb 中, 推荐优先使用
"""
import logging
import os
import time
from functools import wraps

from jenkins import Jenkins, JenkinsException

__all__ = (
    'JenkinsController',
)

from app.config import get_settings

os.environ['PYTHONHTTPSVERIFY'] = '0'


class JenkinsController(Jenkins):
    # class JenkinsController(Jenkins, BaseDataProcess):
    def __init__(self, root: str, path: str, job_name: str):
        # BaseDataProcess.__init__(self, data_list, f'{self.cls_name()}.csv', f'{self.cls_name()}.json')
        settings = get_settings()
        super().__init__(settings.JENKINS_HOST, settings.JENKINS_USERNAME, settings.JENKINS_PASSWORD)
        self.__token = settings.JENKINS_TOKEN
        self.__root = root
        self.__path = path
        self.__job_name = job_name

    @property
    def job_path(self):
        return f'job/{self.__root}/job/{self.__path}/job/{self.__job_name}'

    @property
    def full_project_name(self):
        return '/'.join([seg for seg in [self.__root, self.__path, self.__job_name] if seg])

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def login(self):
        """
        # 获取数据
        """
        try:
            self.get_whoami()
            if not self.get_version():
                logging.error('登录时发生异常')

        except JenkinsException:
            logging.error('登录时发生异常')
        return self

    @staticmethod
    def runtime_status_check(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except JenkinsException as ex:
                return 0, ','.join(ex.args)

        return decorator

    @staticmethod
    def runtime_status_check_with_log_out(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except JenkinsException as ex:
                print(','.join(ex.args))

        return decorator

    def build_job_with_params(self, **params) -> int:
        queue_id = self.build_job(self.full_project_name, params, token=self.__token)
        while True:
            queue_exec_res = self.get_queue_item(queue_id)
            if build_res := queue_exec_res.get('executable'):
                return int(build_res.get('number', -1))
            time.sleep(.1)
