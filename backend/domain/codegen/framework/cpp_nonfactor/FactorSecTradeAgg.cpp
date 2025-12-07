#include "huatai/atsquant/factor/SAMPLE_1S/nonfactor/FactorSecTradeAgg.h"

namespace huatai::atsquant::factor {

  void FactorSecTradeAgg::on_init() { set_sample_mode(false); }


Status FactorSecTradeAgg::calculate() {
  auto seq_no = get_market_data().get_prev_n_quote(1).item<QuoteSchema::Index::TRIGGER_APPL_SEQ_NUM>();
  auto sample_1s_flag = get_sample_flag();

  if (sample_1s_flag && get_factor_manager_param().calculate_mode == FactorManagerParam::CalculateMode::SAMPLE_1S) {
    auto last_quote = get_market_data().get_prev_n_quote(1)[0];
    // 获取采样的时间戳，为上一秒的整秒+1秒
    auto sec_mdtime = (last_quote.item<QuoteSchema::Index::TRIGGER_TIME>() - 1) / 1000 * 1000 + 1000L;
    if (trigger_time_list.size() != 0 and sec_mdtime <= trigger_time_list.back()) {
      sec_mdtime = trigger_time_list.back() + 1000L;
    }
    trigger_time_list.push(sec_mdtime); // 这一整秒的最后一条

    auto trades = get_market_data().get_prev_n_ms_trade(1000, sec_mdtime);
    // auto trades = get_market_data().get_prev_n_ms_trade(1000);
    auto trade_len = trades.len();
    if (trade_len > 0) {
      // 区间范围为上一秒的所有成交数据
      const auto *trade_qtys = trades.item_address<TradeSchema::Index::QUANTITY>();
      const auto *trade_moneys = trades.item_address<TradeSchema::Index::TURNOVER>();
      const auto *trade_sides = trades.item_address<TradeSchema::Index::SIDE>();

      auto active_buy_money = 0.0;
      auto active_sell_money = 0.0;
      auto active_buy_num = 0.0;
      auto active_sell_num = 0.0;
      auto active_buy_volume = 0.0;
      auto active_sell_volume = 0.0;
      auto active_buy_price = 0.0;
      auto active_sell_price = 0.0;

      trades.for_each([&](const RowView<TradeSchema> &rv) {
        trade_price_list.push(rv.item<TradeSchema::Index::PRICE>());
        trade_side_list.push(rv.item<TradeSchema::Index::SIDE>());
        trade_quantity_list.push(rv.item<TradeSchema::Index::QUANTITY>());
        if (rv.item<TradeSchema::Index::SIDE>() == 1) {
          // active_buy_money += rv.item<TradeSchema::Index::TURNOVER>();
          active_buy_money += rv.item<TradeSchema::Index::QUANTITY>() * rv.item<TradeSchema::Index::PRICE>();
          active_buy_volume += rv.item<TradeSchema::Index::QUANTITY>();
          active_buy_num++;
          active_buy_price += rv.item<TradeSchema::Index::PRICE>();
        } else if (rv.item<TradeSchema::Index::SIDE>() == 2) {
          // active_sell_money += rv.item<TradeSchema::Index::TURNOVER>();
          active_sell_money += rv.item<TradeSchema::Index::QUANTITY>() * rv.item<TradeSchema::Index::PRICE>();
          active_sell_volume += rv.item<TradeSchema::Index::QUANTITY>();
          active_sell_num++;
          active_sell_price += rv.item<TradeSchema::Index::PRICE>();
        }
      });

      trade_buy_money_list.push(active_buy_money);
      trade_sell_money_list.push(active_sell_money);
      trade_buy_num_list.push(active_buy_num);
      trade_sell_num_list.push(active_sell_num);
      trade_buy_volume_list.push(active_buy_volume);
      trade_sell_volume_list.push(active_sell_volume);
      trade_net_volume_list.push(active_buy_volume - active_sell_volume);
      trade_buy_price_list.push(active_buy_price);
      trade_sell_price_list.push(active_sell_price);
    } else {
      trade_buy_money_list.push(0.0);
      trade_sell_money_list.push(0.0);
      trade_buy_num_list.push(0.0);
      trade_sell_num_list.push(0.0);
      trade_buy_volume_list.push(0.0);
      trade_sell_volume_list.push(0.0);
      trade_net_volume_list.push(0.0);
      trade_buy_price_list.push(0.0);
      trade_sell_price_list.push(0.0);
    }
  }
  return Status::OK();
}

} // namespace huatai::atsquant::factor
