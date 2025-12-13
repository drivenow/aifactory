# -*- coding: utf-8 -*-
"""
Created on Tue Nov 24 22:48:39 2020
@author: 013150
"""
import re
import ray
import logging
import pandas as pd
from xquant.factorframework.rayframe.util.util import get_factor_attr, parse_extra_data, check_factor_sample_consist
from xquant.factorframework.rayframe.calculation.helper import set_ray_options, get_docker_memory
from xquant.factorframework.rayframe.util.data_context import get_trade_days
from xquant.factorframework.rayframe.FactorDebug import run_hfre_factor_value
from xquant.factorframework.rayframe.MetaFactor import MetaBaseFactor
import os


# class MetaHFBaseFactor(type):
#     def __new__(cls, name, bases, attrs):
#         """
#         attrs: 用户定义的参数
#         类改名，按用户定义的方式
#         """
#         if name == "HfreBaseFactor":
#             return type.__new__(cls, name, bases, attrs)
#
#         for k, v in attrs.items():
#             # 保存类属性和列的映射关系到mappings字典
#             if k == "custom_params":
#                 for subk, subv in attrs["custom_params"].items():
#                     assert type(subv) == int or type(subv) == str, "参数{}类型错误：custom_params只支持传入str或者int类型的参数！".format(
#                         subk)
#                     if type(subv) == str:
#                         assert re.search(r"\W", subv), "参数{}值错误: custom_params只支持传入值为大小写字母、数字或下划线组合的值！".format(subk)
#
#         mapping_name_func = getattr(bases[0], "mapping_name_func", lambda x, y: x)  # 获取高频因子基类中的类命名函数
#         if "custom_params" in attrs:
#             new_name = mapping_name_func(bases[0], name, attrs["custom_params"])
#         else:
#             new_name = name
#         instance = super(MetaHFBaseFactor, cls).__new__(cls, new_name, bases, attrs)
#         setattr(instance, "factor_name", new_name)
#         for k, v in attrs.items():
#             # 覆盖原始因子类中的参数，比如security_type或securities
#             if k != "custom_params":
#                 print("注意：当前正在修改基础因子类的默认类属性{}：{}!".format(k, v))
#                 setattr(instance, k, v)
#         return instance


class HFBaseFactor(object):
    """因子基类
    所有因子的定义都应继承自本类，并重写 calc 方法
    类属性
    factor_type:   高频  (MIN, TICK)
    factor_name:   因子的名称。
    security_type: 因子适用的证券类型， 股票stock 基金fund 债券bond 期货future
    security_pool: 股票池 string or list
    depend_factor: 因子依赖的公共因子或其他的个人因子 String : “因子库名.因子名”
    custom_params: 用户在动态生成因子类的时候可以自由传入参数
    data_input_mode: 用户开发因子需要依赖的行情数据类型：TICK_RAW（原始tick数据），TICK_SAMPLE(采样tick数据)， TRANSACTION_RAW(原始逐笔成交)， TRANSACTION_SAMPLE(采样逐笔成交)
                     ORDER_RAW(原始逐笔委托)，ORDER_SAMPLE(采样逐笔委托)， KLINE1M_RAW（原始分钟K数据）
    """
    def __new__(cls, *args, **kwargs):
        if not hasattr(HFBaseFactor, 'instance_dict'):
            HFBaseFactor.instance_dict = {}

        if str(cls) not in HFBaseFactor.instance_dict.keys():
            instance = super().__new__(cls, *args, **kwargs)
            HFBaseFactor.instance_dict[str(cls)] = instance
            instance.__initialized = False
        return HFBaseFactor.instance_dict[str(cls)]

    factor_type = None  # “MIN”（分钟级）"TICK"(Tick级)
    security_type = None  # 证券类型 stock,future,fund,future,bond
    data_input_mode = []  # 依赖的行情数据类型
    depend_factor_task = []  # 因子依赖的因子加工任务，先只支持一级依赖
    depend_data_task = []  # 因子依赖的数据加工任务，先支持一级依赖
    depend_data = {}  # 依赖的因子数据或者一般数据
    output_factor_names = []  # 输出的因子名，支持多个因子
    custom_params = {}  # 用户在动态生成因子类的时候可以自由传入参数
    # TODO 因子计算需要依赖日行情因子
    depend_factor = []
    