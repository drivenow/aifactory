#include "huatai/atsquant/factor/SAMPLE_1S/nonfactor/FactorSecOrderAgg.h"

namespace huatai::atsquant::factor {


void FactorSecOrderAgg::on_init() { set_sample_mode(false); }

Status FactorSecOrderAgg::calculate() {
  auto seq_no = get_market_data().get_prev_n_quote(1).item<QuoteSchema::Index::TRIGGER_APPL_SEQ_NUM>();
  auto sample_1s_flag = get_sample_flag();

  if (sample_1s_flag && get_factor_manager_param().calculate_mode == FactorManagerParam::CalculateMode::SAMPLE_1S) {
    auto last_quote = get_market_data().get_prev_n_quote(1);
    // 获取采样的时间戳，为上一秒的整秒+1秒
    auto sec_mdtime = (last_quote.item<QuoteSchema::Index::TRIGGER_TIME>() - 1) / 1000 * 1000 + 1000L;
    if (trigger_time_list.size() != 0 and sec_mdtime <= trigger_time_list.back()) {
      sec_mdtime = trigger_time_list.back() + 1000L;
    }
    trigger_time_list.push(sec_mdtime); // 这一整秒的最后一条

    // 获取过去1s的数据，并设置截止时间为整秒
    auto orders = get_market_data().get_prev_n_ms_order(1000, sec_mdtime);
    auto order_len = orders.len();
    if (order_len > 0) {
      // 区间范围为上一秒的所有成交数据
      const auto *order_qtys = orders.item_address<OrderSchema::Index::QUANTITY>();
      const auto *order_sides = orders.item_address<OrderSchema::Index::SIDE>();

      auto active_buy_num = 0.0;
      auto active_sell_num = 0.0;
      auto active_buy_volume = 0.0;
      auto active_sell_volume = 0.0;

      orders.for_each([&](const RowView<OrderSchema> &rv) {
        if (rv.item<OrderSchema::Index::SIDE>() == 1) {
          active_buy_volume += rv.item<OrderSchema::Index::QUANTITY>();
          active_buy_num++;
        } else if (rv.item<OrderSchema::Index::SIDE>() == 2) {
          active_sell_volume += rv.item<OrderSchema::Index::QUANTITY>();
          active_sell_num++;
        }
      });

      order_buy_num_list.push(active_buy_num);
      order_sell_num_list.push(active_sell_num);
      order_buy_volume_list.push(active_buy_volume);
      order_sell_volume_list.push(active_sell_volume);
      order_net_volume_list.push(active_buy_volume - active_sell_volume);
    } else {
      order_buy_num_list.push(0.0);
      order_sell_num_list.push(0.0);
      order_buy_volume_list.push(0.0);
      order_sell_volume_list.push(0.0);
      order_net_volume_list.push(0.0);
    }
  }
  return Status::OK();
}

} // namespace huatai::atsquant::factor
