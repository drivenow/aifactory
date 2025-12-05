#pragma once

#include "huatai/atsquant/factor/base_factor.h"
#include "huatai/atsquant/factor/compute.h"

namespace huatai::atsquant::factor {

class FactorSecTradeAgg : public Factor<> {
  static const int lag1 = 120;
  double prev_real_buy_num = 0.0;
  double prev_real_sell_num = 0.0;

public:
  FACTOR_INIT(FactorSecTradeAgg)
  CircularSlidingWindow<double> trigger_time_list{lag1};
  CircularSlidingWindow<double> trade_real_buy_num_list{lag1};  // 未合并逐笔的成交笔数
  CircularSlidingWindow<double> trade_real_sell_num_list{lag1}; // 未合并逐笔的成交笔数

  CircularSlidingWindow<double> trade_buy_money_list{lag1};
  CircularSlidingWindow<double> trade_sell_money_list{lag1};
  CircularSlidingWindow<double> trade_buy_num_list{lag1};  // 合并同一订单编号的逐笔的成交笔数
  CircularSlidingWindow<double> trade_sell_num_list{lag1}; // 合并同一订单编号的逐笔的成交笔数
  CircularSlidingWindow<double> trade_buy_volume_list{lag1};
  CircularSlidingWindow<double> trade_sell_volume_list{lag1};
  CircularSlidingWindow<double> trade_buy_price_list{lag1};
  CircularSlidingWindow<double> trade_sell_price_list{lag1};
  CircularSlidingWindow<double> trade_net_volume_list{lag1};

  CircularSlidingWindow<double> trade_price_list{lag1};
  CircularSlidingWindow<double> trade_side_list{lag1};
  CircularSlidingWindow<double> trade_quantity_list{lag1};

  void on_init() override;

  Status calculate() override;
};
FACTOR_REGISTER(FactorSecTradeAgg)

} // namespace huatai::atsquant::factor
