from typing import Dict, List
from pathlib import Path
_BASE_DIR = Path(__file__).resolve().parent


class NonfactorMeta:
    def __init__(self, desc: str, fields: Dict[str, str]):
        self.desc = desc
        self.fields = fields

    def to_dict(self):
        return {"desc": self.desc, "fields": self.fields}



PROMPT_FACTOR_L3_CPP_RULE = """
1. **因子逻辑保持一致**

   * 以 Python 因子代码为主参考，如果存在自然语言描述，二者不一致时以 Python 代码为准；
   * 所有数值计算、窗口逻辑、条件判断、边界行为（如长度不足时返回 0）必须与 Python 保持等价。

2. **nonfactor 使用规范（Python 与 C++ 一致）**

   * **禁止**在 C++ 因子中重复从原始 L3 数据（`get_market_data().get_prev_n_quote()` / `get_prev_n_trade()` 等）重新计算已经在 nonfactor 中聚合好的字段；
   * **必须**按照 Python 因子中 `self.get_factor_instance("FactorXXX")` 的依赖关系，在 C++ 中使用 `get_factor<FactorXXX>()` 获取同名 nonfactor；
   * 字段访问规则：

     * Python：`self.nonfactor.some_field_list[-1]`
     * C++：`nonfac->some_field_list.back()` 或 `nonfac->some_field_list[idx]`，其中 `idx` 按 Python 逻辑转换。

3. **C++ 因子框架规范**（参考 SDK 文档与示例）

   * 文件名和类名 **使用与 Python 因子一致的因子名**，如 `FactorBuyWillingByPrice`；
   * 定义参数结构体：`struct FactorBuyWillingByPriceParam { ... };`

     * 仅暴露必要参数，如窗口秒数、阈值等；
     * 使用 `NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(FactorBuyWillingByPriceParam, ...)`；
   * 因子类定义：

     * `class FactorBuyWillingByPrice : public Factor<FactorBuyWillingByPriceParam> { ... };`
     * 使用 `FACTOR_INIT(FactorBuyWillingByPrice)` 宏；
     * `on_init()` 中完成：

       * 所有 `SlidingWindow` 成员的初始化；
       * 调用 `get_factor<FactorSecXXX>()` 获取 nonfactor，并对空指针抛出 `std::runtime_error`；
   * `calculate()` 中：

     * 每次调用先给 `value() = 0;` 做初始化；
     * 根据 nonfactor 向量长度判断是否有足够数据，不足时返回 0；
     * 使用 `compute::` 系列算子完成窗口内计算；
     * 最终将计算结果写入 `value()` 并返回 `Status::OK()`。

4. **预置算子和 SlidingWindow 最佳实践**

   * 对窗口内的累积、均值、方差等运算，**优先使用**:

     * `compute::sum(w, n)`, `compute::mean(w, n)`, `compute::std(w, n)` 等；
     * 对 10 档盘口（买价/卖价/数量/笔数）使用 `compute::sum` 等算子完成加权和，而不是手写逐档循环；
   * 对需要滚动窗口的中间变量，**必须使用 `SlidingWindow` 容器**：

     * 在 `on_init()` 中，用参数（比如 `param().SECONDS`）指定窗口长度；
     * 在 `calculate()` 中按 tick 推进，`push()` 新值，再对整个窗口调用 `compute` 算子。

   * 常用计算算子如下：
      调用方式：compute::算子名()

      | 算子 | 功能 |
      |-----|------|
      | mean | 计算平均值 |
      | std | 标准差 |
      | var | 方差 |
      | median | 中位数 |
      | quantile | 分位数 |
      | diff | 计算相邻元素的差值 |
      | ema | 指数移动平均 |
      | corr | 相关性 |
      | cov | 协方差 |
      | max/min | 最大值、最小值 |
      | imax/imin | 最大值、最小值的索引 |
      | add/sub | 向量加减 |
      | mul/div | 向量相乘、相除 |
      | kurtosis | 峰度 |
      | skewness | 偏度 |
      | sum | 求和 |
      | ewa | 指数加权平均 |


5. **对 Python 中“时间或窗口函数”的映射**

   * 如果 Python 使用上一条或前 N 条采样 1s 值（`[-1]`, `[-2]` 等），在 C++ 中保持 index 逻辑一致；
   * 若 Python 因子里存在类似“过去 N 秒内的统计量”，而其实现已经基于 nonfactor 的 `xxx_list`，则在 C++ 中使用同一个非因子列表 + `SlidingWindow` 和 `compute` 算子表示。
"""


PROMPT_FACTOR_L3_CPP_DEMO = """
以下是一个C++因子的实例：
```cpp

#include "huatai/atsquant/factor/all_factor_types.h"
#include "huatai/atsquant/factor/base_factor.h"
#include "huatai/atsquant/factor/compute.h"

#include "huatai/atsquant/factor/nonfactor/FactorSecOrderBook.h"
#include <cstddef>
namespace huatai::atsquant::factor {
struct FactorBookSell15Move1QtyDeltaDy0TickQtyRatioParam {
  int64_t SECONDS = 300;
};
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(FactorBookSell15Move1QtyDeltaDy0TickQtyRatioParam, SECONDS)

class FactorBookSell15Move1QtyDeltaDy0TickQtyRatio : public Factor<FactorBookSell15Move1QtyDeltaDy0TickQtyRatioParam> {
  std::shared_ptr<FactorSecOrderBook> nonfac;

public:
  FACTOR_INIT(FactorBookSell15Move1QtyDeltaDy0TickQtyRatio)
  // static const int SECONDS = 300;

  // 对于窗口数据，都选用SlidingWindow数据结构,在创建时就指定了窗口大小
  SlidingWindow<double> bigger_ask_vol_qty_queue;
  SlidingWindow<double> ask_vol_qty_queue;
  void on_init() override {
    bigger_ask_vol_qty_queue=SlidingWindow<double>{static_cast<size_t>(param().SECONDS)};
    ask_vol_qty_queue= SlidingWindow<double>{static_cast<size_t>(param().SECONDS)};
    nonfac = get_factor<FactorSecOrderBook>();
    if (nonfac == nullptr) {
      throw std::runtime_error("get nonfactor FactorSecOrderBook error!");
    }
  }

  Status calculate() override {

    value() = 0;

    // 获取nonfactor采样1s的依赖盘口数据，取最新价字段，
    auto size_len = nonfac->last_px_list.size();
    if (size_len < 2) {
      value() = 0;
      auto last_tick = get_market_data().get_prev_n_quote(2);
      bigger_ask_vol_qty_queue.push(0);
      ask_vol_qty_queue.push(compute::sum(last_tick.list_item<QuoteSchema::Index::ASK_QTY>(), 10));
      return Status::OK();
    }
   /////////////////（1）以下为获取nonfactor采样1s的行情数据(首选)///////////////////////
	 // 获取nonfactor采样1s的依赖盘口数据，取十档卖方数量，
    const auto last_ask_qty = nonfac->ask_qty_list[size_len - 2];
    const auto current_ask_qty = nonfac->ask_qty_list.back();

   //   使用框架compute算子，计算前5档委托数量的总和
  // 因为nonfac->ask_qty_list和ask_vol_qty_queue都是SlidingWindow的数据结构，在创建时已经指定了窗口大小, 
    auto sum_ask_v = compute::sum(nonfac->ask_qty_list, 5);
    auto sum_ask_vol_qty = compute::sum(ask_vol_qty_queue, 5);

    	
    // 从nonfactor采样1s的依赖的逐笔聚合1s数据，取成交成交统计量
    size_t idx = nonfac->trade_buy_volume_list.size();
    auto trade_buy_volume_1s = nonfac->trade_buy_volume_list[idx - 1];// 获取最近1s买方成交的统计量
    auto trade_sell_volume_1s = nonfac->trade_sell_volume_list[idx - 1];// 获取最近1s买方成交的统计量

     // 使用框架算子示例：
    auto volumes = quote.item<QuoteSchema::Index::BidVolume>();
    auto avg_vol = compute::mean(volumes);

   /////////////////（2）以下为获取原始行情数据(次选，会重新遍历逐笔，计算量大)///////////////////////
   //获取前n个的tick数据
    auto row_tick = get_market_data().get_prev_n_quote(1);
    // 获取前n秒的trade数据
    auto row_trade = get_market_data().get_prev_n_sec_trade(param().interval);
    value() = 0;
    // 获取盘口的买一和卖一价格
    auto current_tick_ask_p0 = row_tick.list_item<QuoteSchema::Index::ASK_PRICE>()[0];
    auto current_tick_bid_p0 = row_tick.list_item<QuoteSchema::Index::BID_PRICE>()[0];
    return Status::OK();
  }
};
FACTOR_REGISTER(FactorBookSell15Move1QtyDeltaDy0TickQtyRatio)
} // namespace huatai::atsquant::factor
```
"""


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
    )
}

CPP_NONFACTOR_PATH = {
    "FactorSecOrderBook": str(_BASE_DIR / "cpp_nonfactor/FactorSecOrderBook.h"),
    "FactorSecTradeAgg": str(_BASE_DIR / "cpp_nonfactor/FactorSecTradeAgg.h"),
    "FactorSecTradeAgg2": str(_BASE_DIR / "cpp_nonfactor/FactorSecTradeAgg2.h"),
    "FactorSecOrderAgg": str(_BASE_DIR / "cpp_nonfactor/FactorSecOrderAgg.h"),
}