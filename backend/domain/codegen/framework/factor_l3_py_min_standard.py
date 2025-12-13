from typing import Dict, List
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent


class NonfactorMeta:
    def __init__(self, desc: str, fields: Dict[str, str]):
        self.desc = desc
        self.fields = fields

    def to_dict(self):
        return {"desc": self.desc, "fields": self.fields}


# ---------------- Python NonFactors ----------------

PY_NONFACTOR_META = {

    "FactorSecTradeAgg": NonfactorMeta(
        desc="1分钟成交聚合 (Python)",
        fields={
            "trade_buy_money_list": "每分钟买成交金额",
            "trade_sell_money_list": "每分钟卖成交金额",
            "trade_buy_num_list": "每分钟买成交笔数",
            "trade_sell_num_list": "每分钟卖成交笔数",
            "trade_buy_volume_list": "每分钟买成交量",
            "trade_sell_volume_list": "每分钟卖成交量",

        },
    ),
    "FactorSecOrderBook": NonfactorMeta(
        desc="1分钟盘口快照 (Python)",
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
        desc="1分钟订单聚合 (Python)",
        fields={
            "num_bids_sec_list": "每分钟买单笔数",
            "num_asks_sec_list": "每分钟卖单笔数",
            "qty_bids_sec_list": "每分钟买单量",
            "qty_asks_sec_list": "每分钟卖单量",
            "net_volume_sec_list": "每分钟净买量(买-卖)",
        },
    ),
    "NfBaseSec": NonfactorMeta(
        desc="秒级一档数据 (Python)",
        fields={
            "price_list_1s": "每秒最后一条价格",
            "qty_list_1s": "每秒成交量",
            "amt_list_1s": "每秒成交额",
            "level1_buy_qty_list_1s": "每秒买一量",
            "level1_buy_amt_list_1s": "每秒买一金额",
            "level1_sell_qty_list_1s": "每秒卖一量",
            "level1_sell_amt_list_1s": "每秒卖一金额",
        },
    ),
    "FactorLevel": NonfactorMeta(

       desc = "秒级档口数据(Python)",
       fields={
        "level5_avg_buy_price":   "每秒前五档买方均价",
        "level5_avg_sell_price":  "每秒前五档卖方均价",
        "level5_buy_qty_list_1s": "每秒前五档买方挂单量",
        "level5_sell_qty_list_1s": "每秒前五档卖方挂单量",
        "level5_avg_buy_amt_list_1s": "每秒前五档买方挂单金额",
        "level5_avg_sell_amt_list_1s": "每秒前五档卖方挂单金额",
       },
    ),
}

PY_NONFACTOR_PATH = {
    "FactorSecOrderBook": str(_BASE_DIR / "py_nonfactor/FactorSecOrderBook.py"),
    "FactorSecTradeAgg": str(_BASE_DIR / "py_nonfactor/FactorSecTradeAgg.py"),
    "FactorSecOrderAgg": str(_BASE_DIR / "py_nonfactor/FactorSecOrderAgg.py"),
    "NfBaseSec": str(_BASE_DIR / "py_nonfactor/NfBaseSec.py"),
    "FactorLevel":str(_BASE_DIR / "py_nonfactor/FactorLevel.py")
}

PROMPT_FACTOR_L3_PY_RULE = """
### 1. 所有因子类必须满足：
- 类名为 Factor 前缀，例如 FactorBuyWillingByPrice。类名必须和view.factor_name中提供的因子名一模一样。
- 继承 L3FactorFrame.FactorBase: class FactorBuyWillingByPrice(FactorBase):
- 实现固定构造函数签名： def __init__(self, config, factorManager, marketDataManager): super().__init__(config, factorManager, marketDataManager)
- 实现 calculate(self) 方法，在其中完成一次因子计算逻辑。
- 计算结果只能通过 self.addFactorValue(x) 写入，不要 return 值。

### 2. 允许和推荐的 import：
- 必须按需导入框架基础类：
    import numpy as np
    from L3FactorFrame.FactorBase import FactorBase
- 如逻辑确实需要，可以导入 pandas，但请优先使用 numpy 向量运算。
- 不要导入业务无关的第三方库。

### 3. 禁止行为：
- 不允许 import 业务外部模块（除了 numpy 等常规数学库）。
- 不允许文件读写、网络请求等 IO 操作。
- 不允许修改或重定义已有 nonfactor 类（FactorSecOrderBook / FactorSecTradeAgg / FactorSecOrderAgg / NfBaseSec / FactorLevel）。
- 不要在模块顶层执行会产生副作用的代码（例如立即取数、打印、随机数等）。
"""


PROMPT_FACTOR_L3_PY_DEMO_SAMPLE = """
以下是一个Python用Nonfactor采样一分钟计算的示例：

```python
import numpy as np
from L3FactorFrame.FactorBase import FactorBase
from L3FactorFrame.tools.DecimalUtil import isEqual, notEqual

class FactorBuyWillingByPrice(FactorBase):
    def __init__(self, config, factorManager, marketDataManager):
        super().__init__(config, factorManager, marketDataManager)
        self.nonfactor = self.get_factor_instance("FactorSecTradeAgg")
        self.nf = self.get_factor_instance("NfBaseSec")
        self.windows1 = config.get("windows",60)  #时间窗口，此处的单位是分钟
    def calculate(self):
        buy_money = self.nonfactor.trade_buy_money_list[-self.windows:]#取过去60分钟的数据
        sell_money = self.nonfactor.trade_sell_money_list[-self.windows:]
        buy_num = self.nonfactor.trade_buy_num_list[-self.windows:]
        sell_num = self.nonfactor.trade_sell_num_list[-self.windows:]


        sum_v = np.mean(buy_money*buy_num+sell_money*sell*num)
        if sum_v>0:
            self.addFactorValue(sum_v)
        else:
            self.addFactorValue(0.0)
```
"""

PROMPT_FACTOR_L3_PY_MIN_1S = """
以下是一个Python分钟频秒级数据计算的示例:
'''
import numpy as np
from L3FactorFrame.FactorBase import FactorBase
from L3FactorFrame.tools.DecimalUtil import isEqual, notEqual



class FactorNetFlow(FactorBase):
    def __init__(self, config, factorManager, marketDataManager):
        super().__init__(config, factorManager, marketDataManager)
        self.nf = self.get_factor_instance("NfBaseSec")
        self.windows = config.get("windows", 60)  #取过去60秒的数据 
        
        
    def calculate(self):
        bid_amt= self.nf.level1_buy_amt_list_1s[-self.windows:]
        ask_amt= self.nf.level1_sell_amt_list_1s[-self.windows:]
        factor = np.sum(np.array(bid_amt)-np.array(ask_amt))
        
        self.addFactorValue(factor)
'''
"""

PROMPT_FACTOR_L3_PY_DEMO = """
以下是一个Python逐笔数据计算的示例：

```python
class ActivePriceVolume(FactorBase):
    def __init__(self, config, factorManager, marketDataManager):
        super().__init__(config, factorManager, marketDataManager)
        # 配置参数示例，可通过 source_factor_config 配置
        self.__interval = config.get("interval", 8)        # 时间窗口（秒）
        self.price_spread = config.get("price_spread", 0.05)
        self.active_volume = config.get("active_volume", 3000)

    def calculate(self):
        # 1. 采数：逐笔行情 & 逐笔成交
        tickDataIndex = self.getPrevTick("SeqNo")                 # 前一条 L3 逐笔 tick 的 SeqNo
        tradeIndex = self.getPrevTrade("SeqNo")

        asks_price = self.getPrevNTick("AskPrice", 2)             # 前 2 条 L3 逐笔 tick 的买卖价
        bids_price = self.getPrevNTick("BidPrice", 2)

        trade_bs_flag = self.getPrevSecTrade("BSFlag", self.__interval)  # 前 N 秒逐笔成交的字段
        trade_price = self.getPrevSecTrade("Price", self.__interval)
        trade_volume = self.getPrevSecTrade("Volume", self.__interval)

        # 2. 计算因子
        if len(asks_price) < 2:
            factor_value = 0
        else:
            factor_value = 0
            if tickDataIndex == tradeIndex:
                currentTickAskP0, currentTickBidP0 = asks_price[1][0], bids_price[1][0]

                # 条件1：价差
                if currentTickAskP0 - currentTickBidP0 > self.price_spread:
                    # 条件2：主动买/卖量
                    active_buy_volume = np.sum(
                        trade_volume[(trade_bs_flag == 1) & (trade_price >= currentTickBidP0 * 1.0008)]
                    )
                    active_sell_volume = np.sum(
                        trade_volume[(trade_bs_flag == 2) & (trade_price <= currentTickAskP0 * 0.9992)]
                    )
                    # 条件3：主动量阈值
                    if active_buy_volume > self.active_volume:
                        factor_value = 1
                    if active_sell_volume > self.active_volume:
                        factor_value = -1

        self.addFactorValue(factor_value)
```
"""

