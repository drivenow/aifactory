#pragma once

#include "huatai/atsquant/factor/base_factor.h"
#include "huatai/atsquant/factor/compute.h"
#include "huatai/atsquant/factor/contiguous_ring_buffer.h"

namespace huatai::atsquant::factor {

class FactorSecOrderBook : public Factor<> {
  static const int lag1 = 120;

public:
  FACTOR_INIT(FactorSecOrderBook)
  CircularSlidingWindow<double> open_px_list{lag1};
  CircularSlidingWindow<double> mid_px_list{lag1};
  CircularSlidingWindow<double> mid_px_up_flag_list{lag1};
  CircularSlidingWindow<double> last_px_list{lag1};
  CircularSlidingWindow<double> high_px_list{lag1};
  CircularSlidingWindow<double> low_px_list{lag1};
  CircularSlidingWindow<double> total_volume_list{lag1};
  CircularSlidingWindow<double> total_turnover_list{lag1};
  CircularSlidingWindow<double> total_ask_qty_list{lag1};
  CircularSlidingWindow<double> total_bid_qty_list{lag1};
  CircularSlidingWindow<double> avg_ask_price_list{lag1};
  CircularSlidingWindow<double> avg_bid_price_list{lag1};
  CircularSlidingWindow<double> trades_list{lag1};
  CircularSlidingWindow<int> trigger_appl_seq_num_list{lag1};
  CircularSlidingWindow<uint64_t> trigger_time_list{lag1};
  CircularSlidingWindow<const double *> bid_qty_list{lag1};
  CircularSlidingWindow<const double *> bid_price_list{lag1};
  CircularSlidingWindow<const double *> bid_amt_list{lag1};
  CircularSlidingWindow<const uint64_t *> bid_order_nums_list{lag1};
  CircularSlidingWindow<const double *> ask_qty_list{lag1};
  CircularSlidingWindow<const double *> ask_price_list{lag1};
  CircularSlidingWindow<const uint64_t *> ask_order_nums_list{lag1};
  CircularSlidingWindow<const double *> ask_amt_list{lag1};
  void on_init() override;

  Status calculate() override;
};
FACTOR_REGISTER(FactorSecOrderBook)

} // namespace huatai::atsquant::factor
