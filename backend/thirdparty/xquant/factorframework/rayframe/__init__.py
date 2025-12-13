# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     __init__.py
   Description :
   Author :       K0380044
   date：          2019/7/3
-------------------------------------------------
   Change Activity:
                   2019/7/3:
-------------------------------------------------
"""
import ray
from .MetaFactor import MetaBaseFactor
try:
    from .HFBaseFactor import HFBaseFactor  # 可能依赖外部环境，缺失时兜底
except Exception:
    HFBaseFactor = None
from .BaseFactor import Factor


def get_custom_factor_class(BaseFactorClass, class_attrs):
    factor_name = BaseFactorClass.__name__
    if HFBaseFactor:
        assert BaseFactorClass.__base__ == HFBaseFactor or BaseFactorClass.__base__ == Factor, "因子类{}的基类必须为HFBaseFactor或Factor！".format(BaseFactorClass)
    assert type
    return MetaBaseFactor(factor_name, (BaseFactorClass,), class_attrs)
