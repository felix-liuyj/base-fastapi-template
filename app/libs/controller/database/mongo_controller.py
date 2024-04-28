# """
# 使用 mongoengine 引擎, 以 ODM 的方式将获取到的数据存储到 mongodb 中, 推荐优先使用
# """
#
# import json
# from contextlib import contextmanager
# from datetime import datetime
# from typing import Iterable, List, Dict
#
# import pandas as pd
# from mongoengine import Document, ObjectIdField, QuerySet
# from mongoengine.base import BaseField
# from pymongo.collection import Collection
#
# __all__ = (
#     'MongoController',
# )
#
#
# class MongoController:
#     """
#     使用 mongoengine 管理 mongodb
#     初始化: 需要使用全局配置中的存放数据库配置的 DB 类以及控制连接 collection 的 collection 参数进行初始化
#     上下文: 本工具使用推荐使用上下文管理器, 通过 with 关键词进入上下文件时, 本工具将自动连接到数据库并返回自身实例, 退出上下文时能自动断开与数据库的连接
#     """
#
#     def __init__(self, collection: Document, white_list: list = None, compare_key: str = 'name'):
#         self.__clt: Document = collection
#         self.__whitelist = self.__init_wl(white_list)
#         self.__compare_key = compare_key
#         self.__insert_num = self.__update_num = 0
#
#     def __enter__(self):
#         return self
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         return False
#
#     def set_compare_key(self, compare_key: str):
#         self.__compare_key = compare_key
#
#     def __init_wl(self, wl: list):
#         return [
#             key for key, val in self.collection.__dict__.items()
#             if isinstance(val, BaseField) and not isinstance(val, ObjectIdField)
#         ] if not wl else wl
#
#     def select_collection(self, collection: Document, white_list: Iterable = None, compare_key: str = ''):
#         """
#         切换 collection, 仅限当前数据库中存在的表, 也可手动定义数据库 ODM 类后传入\n
#         :param collection: 自定义 collection 名
#         :param white_list: 可选传入白名单
#         :param compare_key: 唯一键
#         """
#         if issubclass(collection, Document):
#             self.__clt = collection
#             self.__whitelist = self.__init_wl(white_list)
#             if compare_key:
#                 self.set_compare_key(compare_key)
#
#         return self
#
#     @contextmanager
#     def select_collection_temporary(self, collection: Document, white_list: Iterable = None, compare_key: str = ''):
#         """
#         临时切换 collection, 为长下文管理器，仅限当前数据库中存在的表, 也可手动定义数据库 ODM 类后传入\n
#         :param collection: 自定义 collection 名
#         :param white_list: 可选传入白名单
#         :param compare_key: 唯一键
#         """
#         legacy_document, legacy_compare_key, legacy_white_list = self.collection, self.__compare_key, self.white_list
#
#         if issubclass(collection, Document):
#             self.__clt = collection
#             self.__whitelist = self.__init_wl(white_list)
#             if compare_key:
#                 self.set_compare_key(compare_key)
#
#         yield self
#
#         self.select_collection(legacy_document, legacy_white_list, legacy_compare_key)
#
#     @property
#     def collection(self) -> Document:
#         """
#         需要使用复杂查询时, 可使用对象内的 collection ODM 类手动查找\n
#         :return: 当前 collection ODM 类
#         """
#         return self.__clt
#
#     @property
#     def white_list(self):
#         return self.__whitelist
#
#     @staticmethod
#     def compare(d_in_db, new_data, white_list):
#         """
#         比较新旧数据, 将有变更的字段并入列表并返回\n
#         :param d_in_db: 数据库中查询到的单条数据
#         :param new_data: 待对比的新数据
#         :param white_list: 字段白名单
#         :return: 需要更新的字段列表
#         """
#         return list(filter(lambda x: True if x else False, [key if getattr(d_in_db, key) != new_data.get(
#             key) else None for key in white_list]))
#
#     def update_db(self, data: (list, dict)):
#         """
#         通过判断 data 的数据类型自动选择 mongodb 写入方法\n
#         :param data: 需要存入数据库的数据, 可以是列表或字典
#         """
#         data = data if isinstance(data, list) else [data]
#         tags = []
#         for s_data in data:
#             tags.append(self.__update(s_data))
#         self.__insert_num, self.__update_num = self.__insert_num + tags.count('i'), self.__update_num + tags.count('u')
#         self.print_count()
#         return self
#
#     def print_count(self):
#         self.__insert_num = self.__update_num = 0
#
#     # noinspection PyMethodParameters
#
#     def update_from_csv(self, filename: str, encoding='gb2312'):
#         """
#         从 csv 文件获取数据并存入数据库\n
#         :param filename: csv 文件名
#         :param encoding: csv 文件编码
#         """
#         csv_reader = pd.read_csv(filename, encoding=encoding)
#         data = json.loads(csv_reader.to_json(orient="records").encode('utf-8'))
#         self.update_db([{key: s_data.get(key, '') for key in self.__whitelist} for s_data in data])
#
#     def delete(self, **condition: dict):
#         """
#         删除数据库中符合条件的一条数据\n
#         :param condition: 查询条件, 为字典
#         """
#         d_in_db = self.__clt.objects(**condition).all()
#         for s_d_in_db in d_in_db:
#             s_d_in_db.delete()
#
#     def query(self, *q, **condition) -> QuerySet:
#         """
#         查询单个
#         :param condition: 条件
#         """
#         return self.__clt.objects(*q, **condition)
#
#     def query_with_expression(self, **expression):
#         """
#         查询单个
#         :param expression: 条件表达式
#         """
#         return self.__clt.objects.filter(**expression)
#
#     def query_include_field(self, field: List[str], *q, **condition) -> QuerySet:
#         """
#         :param field: 需要查询的字段
#         :param condition: 条件
#         """
#         return self.__clt.objects(*q, **condition).only(*field)
#
#     def query_exclude_field(self, field: List[str], *q, **condition) -> QuerySet:
#         """
#         :param field: 需要排除的字段
#         :param condition: 条件
#         """
#         return self.__clt.objects(*q, **condition).exclude(*field)
#
#     def query_one(self, *q, order_by: str = '', **condition) -> Document:
#         """       查询多个
#         :param condition: 条件
#         :param order_by: 排序字段，在字符串前加 ‘+‘、’—’ 分别代表正序、倒序，默认为正序
#         """
#         if order_by:
#             query_set = self.query(*q, **condition).order_by(order_by)
#         else:
#             query_set: QuerySet = self.query(*q, **condition)
#         return query_set.first()
#
#     def query_one_include_field(self, field: List[str], *q, **condition) -> QuerySet:
#         """
#         :param field: 需要查询的字段
#         :param condition: 条件
#         """
#         return self.query_include_field(field, *q, **condition).first()
#
#     def query_one_exclude_field(self, field: List[str], *q, **condition) -> QuerySet:
#         """
#         :param field: 需要排除的字段
#         :param condition: 条件
#         """
#         return self.query_exclude_field(field, *q, **condition).first()
#
#     @staticmethod
#     def group_with_count(query_set: QuerySet, key: str, **kwargs) -> Dict[str, float]:
#         """
#         分组聚合查询，并进行维度倒转，返回由指定字段列表组成数据为值以指定 key 为键的字典\n
#         :param query_set: 查询对象
#         :param key: 分组依据
#         :returns: 维度倒转后的查询结果
#         """
#         condition = [
#             {'$group': {'_id': f'${key}', 'count': {'$sum': 1}}}
#         ]
#         if kwargs.get('extra'):
#             condition.extend(kwargs.get('extra', []))
#         # mongodb 聚合查询只支持最大 16M 的内存，要想去除此限制，需使用 allowDiskUse 参数
#         return {api.get('_id'): api.get('count') for api in list(query_set.aggregate(condition, allowDiskUse=True))}
#
#     def group_with_field_list(self, query_set: QuerySet, key: str, field_list: List[str], **kwargs):
#         """
#         分组聚合查询，并进行维度倒转，返回由指定字段列表组成数据为值以指定 key 为键的字典\n
#         :param query_set: 查询对象
#         :param key: 分组依据
#         :param field_list: 查询结果显示字段
#         :returns: 维度倒转后的查询结果
#         """
#         condition = [
#             {'$group': {'_id': f'${key}', **{field: {'$push': f'${field}'} for field in field_list}}}
#         ]
#         if kwargs.get('match'):
#             condition.append(kwargs.get('match'))
#         # mongodb 聚合查询只支持最大 16M 的内存，要想去除此限制，需使用 allowDiskUse 参数
#         db_data_list: List[dict] = list(query_set.aggregate(condition, allowDiskUse=True))
#         return self.reverse_aggregate_group_result(db_data_list, field_list, **kwargs)
#
#     @staticmethod
#     def reverse_aggregate_group_result(db_data_list: list, field_list: list, single_mode: bool = False) -> dict:
#         """
#         数据维度倒转，分组聚合查询后每条记录的单个字段值会分别组成一个列表\n
#         此时需要将每个字段中的值提取出来还原成记录初始的状态\n
#         :param db_data_list: 分组聚合查询结果
#         :param field_list: 字段列表
#         :param single_mode: 是否单例模式，单例模式下仅返回第一条数据（若存在数据）
#         :returns: 维度倒转后的查询结果
#         """
#         if db_data_list:
#             result = {}
#             for db_data_with_id in db_data_list:
#                 key = db_data_with_id.pop('_id')
#                 values = [dict(zip(field_list, data_set)) for data_set in zip(*list(db_data_with_id.values()))]
#                 result.update({key: values[0] if values and single_mode else values})
#             return result
#         return {}
#
#     def batch_insert(self, data_source: list):
#         """
#         大批量写入，不查重，不验证\n
#         """
#         manager: Collection = self.__clt._get_collection()
#         manager.insert_many(data_source, ordered=False)
#
#     # noinspection PyCallingNonCallable
#     def __update(self, data: dict):
#         """
#         更新数据库, 若待操作数据不存在于数据库中, 则直接添加, 否则使用指定字段( 默认为 name )查询并对比, 将有变更的数据更新
#         :param data: 待操作数据
#         :return: 操作标记, 更新为 u, 插入为 i
#         """
#         if pro_in_db := self.query_one(**{self.__compare_key: data.get(self.__compare_key)}):
#             if chg_l := self.compare(pro_in_db, data, self.__whitelist):
#                 pro_in_db.update(updatedAt=datetime.now().timestamp() * 1000)
#                 [pro_in_db.update(**{key: data.get(key)}) for key in chg_l if data.get(key)]
#                 return 'u'
#         else:
#             data.update(createdAt=datetime.now().timestamp() * 1000)
#             self.__clt(**data).save()
#             return 'i'
#
#     def fill_empty_by_pm_kw(self, cdt, fields_data):
#         self.__update_num = 0
#         cdt_key = list(cdt.keys())[0]
#         condition = {f'{cdt_key}__contains' if '_' not in cdt_key else
#                      f'{cdt_key.split("_")[1]}__{cdt_key.split("_")[0]}': cdt.get(cdt_key)}
#         for s_row in self.__clt.objects(**condition).all():
#             self.__update_num += 1 if s_row.fill_empty_fields(fields_data) else 0
#         return self
