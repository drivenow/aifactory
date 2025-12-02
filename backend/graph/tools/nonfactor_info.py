from typing import Dict, List, Optional
from langchain_core.tools import tool
from .codebase_fs_tools import safe_fs

# --- Nonfactor Metadata Definitions ---

class NonfactorMeta:
    def __init__(self, desc: str, fields: Dict[str, str]):
        self.desc = desc
        self.fields = fields

    def to_dict(self):
        return {
            "desc": self.desc,
            "fields": self.fields
        }

# Simplified metadata based on user provided plan and file contents
NONFACTOR_META_DATA = {
    "FactorSecTradeAgg": NonfactorMeta(
        desc="1秒成交聚合 (FactorSecTradeAgg)",
        fields={
            "trade_buy_money_list": "List[float] - 过去每秒买成交金额",
            "trade_sell_money_list": "List[float] - 过去每秒卖成交金额",
            "trade_buy_num_list": "List[int] - 过去每秒买成交笔数",
            "trade_sell_num_list": "List[int] - 过去每秒卖成交笔数",
            "trade_buy_volume_list": "List[float] - 过去每秒买成交量",
            "trade_sell_volume_list": "List[float] - 过去每秒卖成交量",
        }
    ),
    "FactorSecOrderBook": NonfactorMeta(
        desc="1秒盘口快照 (FactorSecOrderBook)",
        fields={
            "last_px_list": "List[float] - 最新价序列",
            "high_px_list": "List[float] - 最高价序列",
            "low_px_list": "List[float] - 最低价序列",
            "open_px_list": "List[float] - 开盘价序列",
            "total_volume_list": "List[float] - 总成交量序列",
            "total_turnover_list": "List[float] - 总成交额序列",
            "trades_list": "List[int] - 总成交笔数序列",
            "bid_qty_list": "List[float] - 买一量序列",
            "bid_price_list": "List[float] - 买一价序列",
            "bid_order_nums_list": "List[int] - 买一单数序列",
            "ask_qty_list": "List[float] - 卖一量序列",
            "ask_price_list": "List[float] - 卖一价序列",
            "ask_order_nums_list": "List[int] - 卖一单数序列",
        }
    ),
    "FactorSecOrderAgg": NonfactorMeta(
        desc="1秒订单聚合 (FactorSecOrderAgg)",
        fields={
            "num_bids_sec_list": "List[int] - 过去每秒买单笔数",
            "num_asks_sec_list": "List[int] - 过去每秒卖单笔数",
            "qty_bids_sec_list": "List[float] - 过去每秒买单量",
            "qty_asks_sec_list": "List[float] - 过去每秒卖单量",
            "net_volume_sec_list": "List[float] - 过去每秒净买量(买-卖)",
        }
    )
}

# Mapping names to relative file paths
NONFACTOR_PATHS = {
    "FactorSecOrderBook": "backend/graph/tools/NonFactors/FactorSecOrderBook.py",
    "FactorSecTradeAgg": "backend/graph/tools/NonFactors/FactorSecTradeAgg.py",
    "FactorSecOrderAgg": "backend/graph/tools/NonFactors/FactorSecOrderAgg.py",
}


@tool("nonfactor_list")
def nonfactor_list() -> Dict[str, List[Dict[str, str]]]:
    """
    Returns a list of available non-factor components with descriptions.
    Use this to find which base factor/data source to use.
    """
    factors = []
    for name, meta in NONFACTOR_META_DATA.items():
        factors.append({
            "name": name,
            "desc": meta.desc,
            # sample_rate could be added if available, assuming 1s for now based on names
            "sample_rate": "1s" 
        })
    return {"factors": factors}


@tool("nonfactor_source")
def nonfactor_source(name: str) -> Dict:
    """
    Get the source code and metadata structure of a specific non-factor.
    Args:
        name: The name of the non-factor (e.g. 'FactorSecTradeAgg')
    """
    if name not in NONFACTOR_PATHS:
        return {"ok": False, "error": f"Non-factor '{name}' not found."}
    
    file_path = NONFACTOR_PATHS[name]
    read_res = safe_fs.read_file_content(file_path)
    
    if not read_res.get("ok"):
        return {"ok": False, "error": f"Failed to read source: {read_res.get('error')}"}
    
    meta = NONFACTOR_META_DATA.get(name)
    meta_dict = meta.to_dict() if meta else {}
    
    return {
        "ok": True,
        "source": read_res.get("content"),
        "meta": meta_dict
    }
