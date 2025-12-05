#pragma once

#include "huatai/atsquant/factor/base_factor.h"
#include "huatai/atsquant/factor/compute.h"
#include <cstdint>

namespace huatai::atsquant::factor {
// 定义统计状态结构体（保存计算的中间状态）
struct Stats {
  int n = 0;             // 数据点数量
  double mean = 0.0;     // 当前均值
  double sum_mean = 0.0; // 累计均值
  double M = 0.0;        // 当前方差
  double cum_std = 0.0;  // 标准差累积和（用于计算方差）
  double std = 0.0;      // 当前标准差
};
class FactorSecTradeAgg2 : public Factor<> {

  static const int lag1 = 120;

public:
  FACTOR_INIT(FactorSecTradeAgg2)
  CircularSlidingWindow<double> trigger_time_list{lag1};
  CircularSlidingWindow<double> quote_price_bid1_list{lag1};
  CircularSlidingWindow<double> quote_price_ask1_list{lag1};

  CircularSlidingWindow<double> trade_price_num_list{lag1};

  CircularSlidingWindow<double> trade_sell_consum_list{lag1}; // 成交价格大于前一秒卖一价的买数量
  CircularSlidingWindow<double> trade_buy_consum_list{lag1};  // 成交价格大于前一秒买一价的买数量

  CircularSlidingWindow<double> trade_price_num_ob1_list{lag1}; // 成交价大于上一条买一档的个数
  CircularSlidingWindow<double> trade_act_buy_qty_list{lag1};   // 存储当前大于上一秒买一价格的成交量
  CircularSlidingWindow<double> trade_act_sell_qty_list{lag1};  // 存储当前小于上一秒卖一价格的成交量
  CircularSlidingWindow<double> trade_act_buy_num_list{lag1};   // 存储当前大于上一秒买一价格的成交量
  CircularSlidingWindow<double> trade_act_sell_num_list{lag1};  // 存储当前小于上一秒卖一价格的成交量

  CircularSlidingWindow<double> total_ask_amount_list{lag1}; // 买金额
  CircularSlidingWindow<double> total_bid_amount_list{lag1}; // 卖金额

  CircularSlidingWindow<double> total_ask_qty_list{lag1}; // 卖数量
  CircularSlidingWindow<double> total_bid_qty_list{lag1}; // 买数量

  CircularSlidingWindow<double> weight_ask_qty_list{3600};   // 加权买数量
  CircularSlidingWindow<double> weight_bid_qty_list{3600};   // 加权卖数量
                                                             // 3s
  CircularSlidingWindow<double> sum_weight_ask_qty_list{10}; // 累积加权买数量
  CircularSlidingWindow<double> sum_weight_bid_qty_list{10}; // 累积加权卖数量

  // 1s加权买卖数量和
  CircularSlidingWindow<double> sum_weight_ask_qty_1s_list{10}; // 累积加权买数量
  CircularSlidingWindow<double> sum_weight_bid_qty_1s_list{10}; // 累积加权卖数量
  // 1s加权买卖位置和
  CircularSlidingWindow<double> sum_weight_ask_num_1s_list{10}; // 累积加权买数量
  CircularSlidingWindow<double> sum_weight_bid_num_1s_list{10}; // 累积加权卖数量

  CircularSlidingWindow<double> sum_time_weight_ask_amt_1s_list{10}; // 累积加权买数量

  CircularSlidingWindow<double> first_buy_px_list{lag1};
  CircularSlidingWindow<double> first_sell_px_list{lag1};
  CircularSlidingWindow<double> adjst_buy0_px_list{lag1};
  CircularSlidingWindow<double> adjst_sell0_px_list{lag1};

  CircularSlidingWindow<double> bmovs_list{lag1}; // 符合条件的买数量累计和
  CircularSlidingWindow<double> amovs_list{lag1};

  Stats stats{0, 0.0, 0.0, 0.0, 0.0, 0.0};
  int64_t global_buy_cnt = 0;
  int64_t global_sell_cnt = 0;

  void on_init() override;

  Status calculate() override;
};
FACTOR_REGISTER(FactorSecTradeAgg2)

} // namespace huatai::atsquant::factor
