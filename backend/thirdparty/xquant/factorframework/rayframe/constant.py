# -*- coding:utf-8 -*-

from enum import Enum


# 继承枚举类
class DataCollectMode(Enum):
    TICK_RAW = 1  # 原始TICK行情
    TICK_SAMPLE = 2  # 采样后的TICK行情
    TRANSACTION_RAW = 3  # 原始的逐笔成交行情
    TRANSACTION_SAMPLE = 4  # 原始的逐笔成交行情
    ORDER_RAW = 5  # 原始的逐笔委托行情
    ORDER_SAMPLE = 6
    KLINE1M_RAW = 7  # 原始的分钟行情


def transform_datamode(datamode):
    if datamode.upper() == "TICK_RAW":
        return DataCollectMode.TICK_RAW
    elif datamode.upper() == "TICK_SAMPLE":
        return DataCollectMode.TICK_SAMPLE
    elif datamode.upper() == "TRANSACTION_RAW":
        return DataCollectMode.TRANSACTION_RAW
    elif datamode.upper() == "TRANSACTION_SAMPLE":
        return DataCollectMode.TRANSACTION_SAMPLE
    elif datamode.upper() == "ORDER_RAW":
        return DataCollectMode.ORDER_RAW
    elif datamode.upper() == "ORDER_SAMPLE":
        return DataCollectMode.ORDER_SAMPLE
    elif datamode.upper() == "KLINE1M_RAW":
        return DataCollectMode.KLINE1M_RAW
    else:
        raise Exception("datamode目前只支持TICK_RAW、TICK_SAMPLE、TRANSACTION_RAW、TRANSACTION_SAMPLE、ORDER_RAW、KLINE1M_RAW！")
