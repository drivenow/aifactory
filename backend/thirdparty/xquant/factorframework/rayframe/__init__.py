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
from .HFBaseFactor import HFBaseFactor
from .BaseFactor import Factor


def get_custom_factor_class(BaseFactorClass, class_attrs):
    factor_name = BaseFactorClass.__name__
    assert BaseFactorClass.__base__ == HFBaseFactor or BaseFactorClass.__base__ == Factor, "因子类{}的基类必须为HFBaseFactor或Factor！".format(BaseFactorClass)
    assert type
    return MetaBaseFactor(factor_name, (BaseFactorClass,), class_attrs)
