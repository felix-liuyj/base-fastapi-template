"""
存放各种工具
"""
import asyncio
import json
import os
import pathlib
from contextlib import contextmanager, asynccontextmanager
from datetime import datetime, timedelta
from socket import socket, AF_INET, SOCK_DGRAM

from cryptography.fernet import Fernet
from jinja2 import Environment, FileSystemLoader
from rich.console import Console

__all__ = (
    'timing',
    'async_timing',
    'save_to_json',
    'cus_print',
    'update_data',
    'update_dict_in_data',
    'get_xlsx_line',
    'get_local_ip',
    'cur_date',
    'parse_to_utc8',
    'parse_to_utc',
    'parse_timestamp',
    'time_delta',
    'datetime_delta',
    'parse_to_stamp',
    'get_data_from_json',
    'multi_task',
    'run_with_coroutine',
    'encrypt',
    'decrypt',
    'traverse_list_ordinal_possibility',
    'serialize',
    'deserialize',
    'render_template',
)

console = Console()


@contextmanager
def timing(title: str = '', mode='sd'):
    if title:
        cus_print(title, mode)
    start = datetime.now().timestamp()
    yield
    cus_print(f'{datetime.now().timestamp() - start} s', mode)
    if mode == 'p':
        print()


@asynccontextmanager
async def async_timing(title: str = '', mode='sd'):
    if title:
        cus_print(title, mode)
    start = datetime.now().timestamp()
    yield
    cus_print(f'{datetime.now().timestamp() - start} s', mode)
    if mode == 'p':
        print()


def save_to_json(data, path):
    """
    将经过筛选清洗的数据存入 .json 文件。\n
    如果 .json 文件已存在, 且旧数据不是 json 数组, 则将旧数据转加入一个列表后, 合并新旧数据以 json 数组的形式存入。\n
    如果 .json 文件已存在, 且旧数据是 json 数组, 则将新数据并入列表后以 json 数组的形式存入。\n
    """
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    else:
        with open(path, 'r', encoding='utf-8') as f_r:
            legacy_data = json.load(f_r)

            with open(path, 'w', encoding='utf-8') as f_w:
                legacy_data = update_data(legacy_data, data)
                json.dump(legacy_data, f_w)
    cus_print('已成功写入数据到 json 文件', 'sc')


def update_data(legacy_data, new_data):
    for s_d_wid in new_data:
        if s_d_wid.get('id') in [s.get('id') for s in legacy_data]:
            for s_l_d in legacy_data:
                if s_l_d.get('id') == s_d_wid.get('id'):
                    index = legacy_data.index(s_l_d)
                    is_update, s_l_d = update_dict_in_data(s_d_wid, s_l_d)
                    if is_update:
                        legacy_data[index] = s_l_d
                    break
        else:
            legacy_data.append(s_d_wid)
    return legacy_data


def update_dict_in_data(s_d_wid, s_l_d):
    is_update = False
    for key, val in s_d_wid.items():
        if (key in s_l_d.keys() and val != s_l_d.get(key)) or key not in s_l_d.keys():
            (s_l_d.update({key: val}))
            is_update = True
    return is_update, s_l_d


def get_xlsx_line(df, s_pro, col, kw):
    """
    从Excel中通过指定的字段匹配所在行\n
    :return: 匹配到的数据以及原数据(字典)
    """
    result = df.drop(columns=list(filter(lambda x: True if 'Unnamed' in x else False, list(df.columns))),
                     axis=1).fillna(value='')[(getattr(df, col) == s_pro.get(kw))].to_dict(orient='records')
    result = result[-1] if result else {}
    return result, s_pro


def cus_print(print_str: str, mode: str = 'l', end: str = '\n'):
    """
    自定义控制台输出, 使其能在输出的同时制定输出颜色\n
    :param print_str: 需要输出的字符串
    :param mode: 字体颜色: w: 警告warning 红色, sc: 成功success 绿色, t: 提示tips 黄色, p: 重要primary 蓝色, sd: 次要secondary 青蓝色, l: 日志log 白色
    :param end:
    """
    cs_p_c_t = {'w': 'red', 'sc': 'green', 't': 'yellow', 'p': 'blue', 'sd': 'cyan', 'l': 'white'}
    console.print(f'[bold {cs_p_c_t.get(mode)}]{print_str}', end=end)


def get_local_ip():
    """
    建立与本地的 UDP 连接获取本地 IP\n
    :return: 本地 IP
    """
    s = None
    try:
        s = socket(AF_INET, SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception as ex:
        cus_print(f'socket 运行异常{ex}', 'w')
        s.close() if s else None
        ip = None
    return ip


def cur_date(mode: str = 'date'):
    """
    以不同模式获取获取当天时间\n
    :param mode: 模式, date: 精确到日期, month: 精确到月, year: 仅年份, full: 精确到秒, timestamp: 时间戳（秒）, timestamp_ms: 时间戳（毫秒）
    """
    from datetime import datetime
    date = datetime.now()
    return {
        'date': [date.year, date.month, date.day],
        'month': [date.year, date.month],
        'year': [date.year],
        'full': [date.year, date.month, date.day, date.hour, date.minute, date.second],
        'timestamp': int(date.timestamp()),
        'timestamp_ms': int(date.timestamp() * 1000)
    }.get(mode)


def parse_to_utc8(utc: str | int | float, time_f: str = '%Y-%m-%d %H:%M:%S', mode='format'):
    date = datetime.fromtimestamp(utc) if isinstance(utc, (float, int)) else datetime.strptime(utc, time_f)
    utc8 = date + timedelta(hours=8)
    return {
        'format': utc8.strftime(time_f),
        'stamp': utc8.timestamp()
    }.get(mode)


def parse_to_utc(utc8: str | float, time_f: str = '%Y-%m-%d %H:%M:%S', mode='format'):
    date = datetime.fromtimestamp(utc8) if isinstance(utc8, float) else datetime.strptime(utc8, time_f)
    utc = date - timedelta(hours=8)
    return {
        'format': utc.strftime(time_f),
        'stamp': utc.timestamp()
    }.get(mode)


def parse_timestamp(stamp: float, time_f: str = '%Y-%m-%d %H:%M:%S', mode='format'):
    utc8 = datetime.fromtimestamp(stamp)
    return {
        'format': utc8.strftime(time_f),
    }.get(mode)


def time_delta(origin, time_f: str = '%Y-%m-%d', increment: int = 1, **delta: dict):
    result = datetime.strptime(origin, time_f) + timedelta(**delta) * increment
    return result.strftime(time_f)


def datetime_delta(origin: datetime, time_f: str = '%Y-%m-%d', increment: int = 1, **delta: dict):
    result = origin + timedelta(**delta) * increment
    return result.strftime(time_f)


def parse_to_stamp(utc, time_f: str = '%Y-%m-%d %H:%M:%S'):
    return int(datetime.strptime(utc, time_f).timestamp()) * 1000


def get_data_from_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def multi_task(process_method, container, data_list: list, *args, select_mode=False, **kwargs):
    from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
    import multiprocessing

    executor = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count() if multiprocessing.cpu_count() < 10 else 10)
    wait([executor.submit(
        process_method.get(data) if select_mode else process_method, container, data, ind, *args, **kwargs
    ) for ind, data in enumerate(data_list)], return_when=ALL_COMPLETED)


def encrypt(origin: str, key: str):
    cipher_suite = Fernet(key)
    return cipher_suite.encrypt(origin.encode('utf-8')).decode('utf-8')


def decrypt(encrypted_str: str, key: str) -> str:
    cipher_suite = Fernet(key)
    return cipher_suite.decrypt(encrypted_str.encode('utf-8')).decode('utf-8')


def traverse_list_ordinal_possibility(container: list, source: list, tier: int, start: int = 0, item: list = None):
    """
    遍历列表中随机 N 项的顺序的可能性\n
    例：[1, 2, 3] => [(1, 2), (1, 3), (2, 3)]\n
    :param container: 容器
    :param source: 数据源
    :param tier: 层级，即每种可能性包含的元素
    :param start: 起始索引
    :param item: 单个可能性
    """
    tier = len(source) if len(source) < tier else tier
    if tier - 1 > 0:
        for i in range(start, len(source)):
            traverse_list_ordinal_possibility(container, source, tier - 1, i + 1, [*(item or []), source[i]])
    else:
        [container.append((*(item or []), d)) for d in source[start:]]


async def run_with_coroutine(func: callable, data_pool: list, *args, **kwargs):
    # 创建任务列表
    tasks = [asyncio.create_task(func(item, *args, **kwargs)) for item in data_pool]
    # 等待所有任务完成
    await asyncio.gather(*tasks)


def serialize(obj: dict | list) -> str:
    """
    将字典或列表序列化为字符串
    :param obj:
    :return:
    """
    return json.dumps(obj, ensure_ascii=False).encode('utf-8')


def deserialize(obj_str: str) -> dict:
    """
    将字符串反序列化为字典
    :rtype: object
    :param obj_str:
    :return:
    """
    return json.loads(obj_str)


def render_template(template_name: str, **render_data: dict) -> str:
    # Create an Environment object that specifies how the template will be loaded as a file system
    env = Environment(loader=FileSystemLoader(f'{pathlib.Path(__file__).resolve().parent.parent}/templates'))
    # Load a template file, the contents of which is an HTML page with some placeholders
    template = env.get_template(template_name)
    # Call the template's render method, pass in the data, and get the final document.
    return template.render({'data': render_data})
