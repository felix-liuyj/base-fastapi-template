import abc
import json
from contextlib import contextmanager
from typing import List

import pandas as pd
from requests.exceptions import SSLError

from .custom import cus_print


class BaseDataProcess:
    """
    数据处理基类, 为派生类提供保存数据到文件的方法以及抽象出登录 login 方法，限制其派生类必须实现此方法
    初始化: 由派生类完成, 指定 csv 与 json 文件名, 指定初始数据
    文件写入: 提供 save_to_file, save_to_json, save_to_csv 三个方法, 可选择 csv, json 两者都写入或者二选一
    """

    def __init__(self, result, csv_file, json_file):
        self.result: list | dict | None = result
        self.csv_file = csv_file
        self.json_file = json_file

    def __enter__(self):
        self.login()
        return self

    async def __aenter__(self):
        await self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    @classmethod
    def cls_name(cls):
        return cls.__name__

    @abc.abstractmethod
    async def login(self):
        pass

    @contextmanager
    def request_get(self, api_url):
        pass

    @property
    def json_result(self):
        return json.dumps(self.result, ensure_ascii=False)

    def save_to_file(self, data_source: list, filepath: str = ''):
        cus_print(f'正在将数据写入到 {filepath}', 't')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(data_source)
            cus_print(f'已成功写入\n', 'sc')
        return self

    def save_to_json(self, data_source: List[dict], filepath: str = ''):
        filepath = filepath if filepath else self.json_file
        cus_print(f'正在将数据写入到 {filepath}', 't')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_source if data_source else self.result, f, ensure_ascii=False)
            cus_print(f'已成功写入\n', 'sc')
        return self

    def save_to_csv(self, data_source: List[dict], filepath: str = ''):
        filepath = filepath if filepath else self.csv_file
        cus_print(f'正在将数据写入到 {filepath}', 't')
        pd.DataFrame(data_source if data_source else self.result).to_csv(
            path_or_buf=filepath, mode='w', index=False
        )
        cus_print('已成功写入\n', 'sc')
        return self

    @staticmethod
    @contextmanager
    def req_status_monitor():
        """
        上下文管理器, 自动捕获 SSLError 异常\n
        """
        try:
            yield
        except SSLError as e:
            cus_print(f'something has errors: {e}', 'w')
