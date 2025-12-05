#pragma once

#include "huatai/atsquant/factor/base_factor.h"
#include "huatai/atsquant/factor/compute.h"

namespace huatai::atsquant::factor {

class FactorSecOrderAgg : public Factor<> {
  static const int lag1 = 120;

public:
  FACTOR_INIT(FactorSecOrderAgg)
  CircularSlidingWindow<double> trigger_time_list{lag1};
  CircularSlidingWindow<double> order_buy_num_list{lag1};
  CircularSlidingWindow<double> order_sell_num_list{lag1};
  CircularSlidingWindow<double> order_buy_volume_list{lag1};
  CircularSlidingWindow<double> order_sell_volume_list{lag1};
  CircularSlidingWindow<double> order_net_volume_list{lag1}; // buy -sell
  void on_init() override;

  Status calculate() override;
};
FACTOR_REGISTER(FactorSecOrderAgg)

} // namespace huatai::atsquant::factor
