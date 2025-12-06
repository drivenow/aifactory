from typing import Dict, List
from pathlib import Path
from langchain_core.tools import tool


class NonfactorMeta:
    def __init__(self, desc: str, fields: Dict[str, str]):
        self.desc = desc
        self.fields = fields

    def to_dict(self):
        return {"desc": self.desc, "fields": self.fields}


_BASE_DIR = Path(__file__).resolve().parent

# ---------------- Python NonFactors ----------------

PY_NONFACTOR_META = {
    "FactorSecTradeAgg": NonfactorMeta(
        desc="1秒成交聚合 (Python)",
        fields={
            "trade_buy_money_list": "每秒买成交金额",
            "trade_sell_money_list": "每秒卖成交金额",
            "trade_buy_num_list": "每秒买成交笔数",
            "trade_sell_num_list": "每秒卖成交笔数",
            "trade_buy_volume_list": "每秒买成交量",
            "trade_sell_volume_list": "每秒卖成交量",
        },
    ),
    "FactorSecOrderBook": NonfactorMeta(
        desc="1秒盘口快照 (Python)",
        fields={
            "last_px_list": "最新价序列",
            "high_px_list": "最高价序列",
            "low_px_list": "最低价序列",
            "open_px_list": "开盘价序列（首次用总额/总量估算）",
            "total_volume_list": "总成交量序列",
            "total_turnover_list": "总成交额序列",
            "trades_list": "总成交笔数序列",
            "bid_qty_list": "买一量序列",
            "bid_price_list": "买一价序列",
            "bid_order_nums_list": "买一挂单笔数序列",
            "ask_qty_list": "卖一量序列",
            "ask_price_list": "卖一价序列",
            "ask_order_nums_list": "卖一挂单笔数序列",
            "trigger_appl_seq_num_list": "触发序列号",
            "trigger_time_list": "触发时间（整秒）",
        },
    ),
    "FactorSecOrderAgg": NonfactorMeta(
        desc="1秒订单聚合 (Python)",
        fields={
            "num_bids_sec_list": "每秒买单笔数",
            "num_asks_sec_list": "每秒卖单笔数",
            "qty_bids_sec_list": "每秒买单量",
            "qty_asks_sec_list": "每秒卖单量",
            "net_volume_sec_list": "每秒净买量(买-卖)",
        },
    ),
}

PY_NONFACTOR_PATHS = {
    "FactorSecOrderBook": str(_BASE_DIR / "py_nonfactor/FactorSecOrderBook.py"),
    "FactorSecTradeAgg": str(_BASE_DIR / "py_nonfactor/FactorSecTradeAgg.py"),
    "FactorSecOrderAgg": str(_BASE_DIR / "py_nonfactor/FactorSecOrderAgg.py"),
}

# ---------------- C++ NonFactors ----------------

CPP_NONFACTOR_META = {
    "FactorSecTradeAgg": NonfactorMeta(
        desc="1秒成交聚合 (C++)",
        fields={
            "trigger_time_list": "采样时间戳(ms)",
            "trade_real_buy_num_list": "逐笔买成交笔数（未合并单号）",
            "trade_real_sell_num_list": "逐笔卖成交笔数（未合并单号）",
            "trade_buy_money_list": "买成交金额（数量*价格累加）",
            "trade_sell_money_list": "卖成交金额（数量*价格累加）",
            "trade_buy_num_list": "买成交笔数（同订单合并）",
            "trade_sell_num_list": "卖成交笔数（同订单合并）",
            "trade_buy_volume_list": "买成交量",
            "trade_sell_volume_list": "卖成交量",
            "trade_buy_price_list": "买成交价累加（需自行均值化）",
            "trade_sell_price_list": "卖成交价累加（需自行均值化）",
            "trade_net_volume_list": "净成交量（买-卖）",
            "trade_price_list": "逐笔成交价序列",
            "trade_side_list": "逐笔成交方向(1买/2卖)",
            "trade_quantity_list": "逐笔成交量序列",
        },
    ),
    "FactorSecTradeAgg2": NonfactorMeta(
        desc="成交价穿透/买卖压力扩展 (C++)",
        fields={
            "trigger_time_list": "采样时间戳(ms)",
            "quote_price_bid1_list": "上一秒买一价",
            "quote_price_ask1_list": "上一秒卖一价",
            "trade_price_num_list": "成交价个数",
            "trade_sell_consum_list": "成交价大于前一秒卖一价的买数量",
            "trade_buy_consum_list": "成交价小于前一秒买一价的卖数量",
            "trade_price_num_ob1_list": "成交价大于上一条买一档的个数",
            "trade_act_buy_qty_list": "大于上一秒买一价的成交量",
            "trade_act_sell_qty_list": "小于上一秒卖一价的成交量",
            "trade_act_buy_num_list": "大于上一秒买一价的成交笔数",
            "trade_act_sell_num_list": "小于上一秒卖一价的成交笔数",
            "total_ask_amount_list": "买金额",
            "total_bid_amount_list": "卖金额",
            "total_ask_qty_list": "卖数量",
            "total_bid_qty_list": "买数量",
            "weight_ask_qty_list": "加权买数量（长窗口）",
            "weight_bid_qty_list": "加权卖数量（长窗口）",
            "sum_weight_ask_qty_list": "累积加权买数量",
            "sum_weight_bid_qty_list": "累积加权卖数量",
            "sum_weight_ask_qty_1s_list": "1s累积加权买数量",
            "sum_weight_bid_qty_1s_list": "1s累积加权卖数量",
            "sum_weight_ask_num_1s_list": "1s累积加权买笔数",
            "sum_weight_bid_num_1s_list": "1s累积加权卖笔数",
            "sum_time_weight_ask_amt_1s_list": "1s时间加权买金额",
            "first_buy_px_list": "首个买价",
            "first_sell_px_list": "首个卖价",
            "adjst_buy0_px_list": "调整后买价",
            "adjst_sell0_px_list": "调整后卖价",
            "bmovs_list": "满足条件的买数量累计",
            "amovs_list": "满足条件的卖数量累计",
        },
    ),
    "FactorSecOrderBook": NonfactorMeta(
        desc="1秒盘口快照 (C++)",
        fields={
            "open_px_list": "开盘价序列（首日用总额/总量估算）",
            "mid_px_list": "买卖一均价",
            "mid_px_up_flag_list": "中间价上行标记(1/0)",
            "last_px_list": "最新价序列",
            "high_px_list": "最高价序列",
            "low_px_list": "最低价序列",
            "total_volume_list": "总成交量序列",
            "total_turnover_list": "总成交额序列",
            "total_ask_qty_list": "盘口总卖量",
            "total_bid_qty_list": "盘口总买量",
            "avg_ask_price_list": "加权平均卖价（有量时）",
            "avg_bid_price_list": "加权平均买价（有量时）",
            "trades_list": "总成交笔数",
            "trigger_appl_seq_num_list": "触发序列号",
            "trigger_time_list": "触发时间戳(ms)",
            "bid_qty_list": "买1-10档数量数组指针",
            "bid_price_list": "买1-10档价格数组指针",
            "bid_order_nums_list": "买1-10档挂单笔数数组指针",
            "bid_amt_list": "买1-10档金额数组指针",
            "ask_qty_list": "卖1-10档数量数组指针",
            "ask_price_list": "卖1-10档价格数组指针",
            "ask_order_nums_list": "卖1-10档挂单笔数数组指针",
            "ask_amt_list": "卖1-10档金额数组指针",
        },
    ),
    "FactorSecOrderAgg": NonfactorMeta(
        desc="1秒订单聚合 (C++)",
        fields={
            "trigger_time_list": "采样时间戳(ms)",
            "order_buy_num_list": "每秒买单笔数",
            "order_sell_num_list": "每秒卖单笔数",
            "order_buy_volume_list": "每秒买单量",
            "order_sell_volume_list": "每秒卖单量",
            "order_net_volume_list": "每秒净买量(买-卖)",
        },
    ),
    "PriceSpread": NonfactorMeta(
        desc="价差辅助组件 (C++)",
        fields={"sample_value": "价差示例数据（vector<double>）"},
    ),
}

CPP_NONFACTOR_PATHS = {
    "FactorSecOrderBook": str(_BASE_DIR / "cpp_nonfactor/FactorSecOrderBook.h"),
    "FactorSecTradeAgg": str(_BASE_DIR / "cpp_nonfactor/FactorSecTradeAgg.h"),
    "FactorSecTradeAgg2": str(_BASE_DIR / "cpp_nonfactor/FactorSecTradeAgg2.h"),
    "FactorSecOrderAgg": str(_BASE_DIR / "cpp_nonfactor/FactorSecOrderAgg.h"),
    "PriceSpread": str(_BASE_DIR / "cpp_nonfactor/PriceSpread.h"),
}


def _format_meta_block(title: str, meta_map: Dict[str, NonfactorMeta]) -> str:
    lines = [title]
    for name, meta in meta_map.items():
        lines.append(f"\n--- {name} ---")
        lines.append(meta.desc)
        for field, desc in meta.fields.items():
            lines.append(f"- {field}: {desc}")
    return "\n".join(lines)


def get_formatted_nonfactor_info_py() -> str:
    """Python NonFactor字段与源码摘要。"""
    info = _format_meta_block("【Python NonFactors 字段】", PY_NONFACTOR_META)
    lines = [info, "\n【Python NonFactors 源码】"]
    for name, path in PY_NONFACTOR_PATHS.items():
        lines.append(f"\n--- {name} ---")
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines.append(f.read())
        except Exception as e:
            lines.append(f"Error reading source: {e}")
    return "\n".join(lines)


def get_formatted_nonfactor_info_cpp() -> str:
    """C++ NonFactor字段与源码摘要。"""
    info = _format_meta_block("【C++ NonFactors 字段】", CPP_NONFACTOR_META)
    lines = [info, "\n【C++ NonFactors 头文件】"]
    for name, path in CPP_NONFACTOR_PATHS.items():
        lines.append(f"\n--- {name} ---")
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines.append(f.read())
        except Exception as e:
            lines.append(f"Error reading source: {e}")
    return "\n".join(lines)
