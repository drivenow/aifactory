#include "huatai/atsquant/factor/SAMPLE_1S/nonfactor/FactorSecTradeAgg2.h"
#include "huatai/atsquant/factor/schema.h"
#include <cmath>
#include <vector>

namespace huatai::atsquant::factor {

  void FactorSecTradeAgg2::on_init() { set_sample_mode(false); }


// 函数：输入新数据点，更新统计状态
void update_stats(Stats &stats, double new_value) {
  stats.n++;
  double delta = new_value - stats.mean;
  stats.mean += new_value / stats.n; // 更新均值
  stats.sum_mean += stats.mean;      // 计算累计均值
  double delta2 = new_value - stats.mean;

  stats.M = stats.M + delta * delta2;                              // 计算当前方差
  double variance = (stats.n > 1) ? stats.M / (stats.n - 1) : 0.0; // 计算方差
  stats.std = sqrt(variance);                                      // 求标准差
  stats.cum_std += stats.std;                                      // 更新标准差累积和
}

Status FactorSecTradeAgg2::calculate() {
  auto seq_no = get_market_data().get_prev_n_quote(1).item<QuoteSchema::Index::TRIGGER_APPL_SEQ_NUM>();
  auto sample_1s_flag = get_sample_flag();

  if (sample_1s_flag && get_factor_manager_param().calculate_mode == FactorManagerParam::CalculateMode::SAMPLE_1S) {

    auto last_quote = get_market_data().get_prev_n_quote(1)[0];
    quote_price_bid1_list.push(last_quote.list_item<QuoteSchema::Index::BID_PRICE>()[0]);
    quote_price_ask1_list.push(last_quote.list_item<QuoteSchema::Index::ASK_PRICE>()[0]);
    double last_1s_bid1_price = 0.0; // 上一秒的买一价
    double last_1s_ask1_price = 1e8; // 上一秒的卖一价
    // 等于上一秒卖一价的买数量和
    double over_last_1s_s1_buy_qty = 0.0;
    // 等于上一秒买一价的买数量和
    double over_last_1s_b1_sell_qty = 0.0;
    double last_1s_low_px = last_quote.item<QuoteSchema::Index::LOW_PX>();
    double last_1s_high_px = last_quote.item<QuoteSchema::Index::HIGH_PX>();

    if (quote_price_bid1_list.size() > 1) {
      last_1s_bid1_price = quote_price_bid1_list[quote_price_bid1_list.size() - 2];
      last_1s_bid1_price = last_1s_bid1_price < 1e-6 ? last_1s_low_px : last_1s_bid1_price;
      last_1s_ask1_price = quote_price_ask1_list[quote_price_ask1_list.size() - 2];
      last_1s_ask1_price = last_1s_ask1_price < 1e-6 ? last_1s_high_px : last_1s_ask1_price;
    }

    // 获取采样的时间戳，为上一秒的整秒+1秒
    auto sec_mdtime = (last_quote.item<QuoteSchema::Index::TRIGGER_TIME>() - 1) / 1000 * 1000 + 1000L;
    if (trigger_time_list.size() != 0 and sec_mdtime <= trigger_time_list.back()) {
      sec_mdtime = trigger_time_list.back() + 1000L;
    }
    trigger_time_list.push(sec_mdtime); // 这一整秒的最后一条

    auto trades = get_market_data().get_prev_n_ms_trade(1000, sec_mdtime);
    auto trade_len = trades.len();
    auto active_over_b1_num = 0.0;
    auto active_over_s1_num = 0.0;
    auto total_buy_qty = 0.0;
    auto total_sell_qty = 0.0;
    auto act_buy_qty = 0.0;
    auto act_sell_qty = 0.0;
    auto act_buy_num = 0.0;
    auto act_sell_num = 0.0;
    auto total_buy_amount = 0.0;
    auto total_sell_amount = 0.0;
    int count_buy = 0;
    int count_sell = 0;
    auto sum_sell = 0.0;
    auto sum_buy = 0.0;
    // std::vector<double> qty_vec;
    // std::vector<double> price_vec;

    int count_buy_1s = 0;
    int count_sell_1s = 0;
    int64_t count = 0;
    double sum_weight_sell_1s = 0.0;
    double sum_weight_buy_1s = 0.0;
    double sum_weight_sell_num_1s = 0.0;
    double sum_weight_buy_num_1s = 0.0;
    double buy_px_over_b1_num = 0.0;
    double sell_px_over_b1_num = 0.0;
    double time_weight_amt = 0.0;

    if (trade_len > 0) {
      // 区间范围为上一秒的所有成交数据
      const auto *trade_times = trades.item_address<TradeSchema::Index::TIMESTAMP>();
      const auto *trade_qtys = trades.item_address<TradeSchema::Index::QUANTITY>();
      const auto *trade_moneys = trades.item_address<TradeSchema::Index::TURNOVER>();
      const auto *trade_sides = trades.item_address<TradeSchema::Index::SIDE>();
      double last_trade_time = trade_times[trades.size() - 1];

      // qty_vec.clear();
      // price_vec.clear();
      trades.for_each([&](const RowView<TradeSchema> &rv) {
        count++;
        if (rv.item<TradeSchema::Index::PRICE>() >= last_1s_bid1_price) {
          active_over_b1_num += 1;
        }
        if (rv.item<TradeSchema::Index::SIDE>() == 1) {
          auto trade_px = rv.item<TradeSchema::Index::PRICE>();
          auto trade_qty = rv.item<TradeSchema::Index::QUANTITY>();
          if (std::fabs(trade_px - last_1s_ask1_price) < 1e-4) {
            over_last_1s_s1_buy_qty += trade_qty;
          }
          total_buy_amount += rv.item<TradeSchema::Index::TURNOVER>();
          total_buy_qty += rv.item<TradeSchema::Index::QUANTITY>();
          count_buy_1s += 1; // 买计数
          global_buy_cnt++;
          auto weight_qty = pow(0.5, count_buy_1s) * rv.item<TradeSchema::Index::TURNOVER>();
          sum_weight_buy_1s += weight_qty;
          // auto weight_num = pow(0.5, global_buy_cnt);
          // sum_weight_buy_num_1s += weight_num;

          if (rv.item<TradeSchema::Index::PRICE>() - last_1s_bid1_price > 1e-4) {
            act_buy_qty += rv.item<TradeSchema::Index::QUANTITY>();
            act_buy_num += 1;
            // auto tmp_value = rv.item<TradeSchema::Index::QUANTITY>();
            // qty_vec.push_back(tmp_value);
            // auto tmp_price = rv.item<TradeSchema::Index::PRICE>();
            // price_vec.push_back(tmp_price);
            update_stats(stats, rv.item<TradeSchema::Index::QUANTITY>());
          }
        }
        if (rv.item<TradeSchema::Index::SIDE>() == 2) {
          auto trade_px = rv.item<TradeSchema::Index::PRICE>();
          auto trade_qty = rv.item<TradeSchema::Index::QUANTITY>();
          if (std::fabs(trade_px - last_1s_bid1_price) < 1e-4) {
            over_last_1s_b1_sell_qty += trade_qty;
          }
          total_sell_qty += rv.item<TradeSchema::Index::QUANTITY>();
          total_sell_amount += rv.item<TradeSchema::Index::TURNOVER>();
          count_sell_1s++;
          global_sell_cnt++;
          auto weight_qty = pow(0.5, count_sell_1s) * rv.item<TradeSchema::Index::QUANTITY>();
          sum_weight_sell_1s += weight_qty;
          // auto weight_num = pow(0.5, global_sell_cnt);
          // sum_weight_sell_num_1s += weight_num;

          if (rv.item<TradeSchema::Index::PRICE>() < last_1s_ask1_price - 1e-6) {
            act_sell_qty += rv.item<TradeSchema::Index::QUANTITY>();
            act_sell_num += 1;
            // auto tmp_value = rv.item<TradeSchema::Index::QUANTITY>();
            // qty_vec.push_back(tmp_value);
            // auto tmp_price = rv.item<TradeSchema::Index::PRICE>();
            // price_vec.push_back(tmp_price);
            update_stats(stats, rv.item<TradeSchema::Index::QUANTITY>());
          }

          double time_delta = (rv.item<TradeSchema::Index::TIMESTAMP>() - last_trade_time) / 1000.0;
          time_weight_amt +=
              std::exp(time_delta) * rv.item<TradeSchema::Index::QUANTITY>() * rv.item<TradeSchema::Index::PRICE>();
        }
      });

      // auto trades_3s = get_market_data().get_prev_n_ms_trade(3000);
      auto trades_3s = get_market_data().get_prev_n_ms_trade(3000, sec_mdtime);
      trades_3s.for_each([&](const RowView<TradeSchema> &rv) {
        if (rv.item<TradeSchema::Index::SIDE>() == 1) {
          count_buy += 1; // 买计数
          auto rv_buy_qty = rv.item<TradeSchema::Index::QUANTITY>();
          auto rv_buy_time = rv.item<TradeSchema::Index::TIMESTAMP>();
          auto rv_buy_px = rv.item<TradeSchema::Index::PRICE>();
          auto weight_qty = pow(0.5, count_buy);
          weight_bid_qty_list.push(weight_qty);
          // auto sum = compute::sum(weight_bid_qty_list);
          sum_buy += weight_qty;
          auto weight_num = pow(0.5, count_buy);
          sum_weight_buy_num_1s += weight_num;
        }
        if (rv.item<TradeSchema::Index::SIDE>() == 2) {
          count_sell += 1; // 卖计数
          auto rv_sell_qty = rv.item<TradeSchema::Index::QUANTITY>();
          auto rv_sell_px = rv.item<TradeSchema::Index::PRICE>();
          auto rv_sell_time = rv.item<TradeSchema::Index::TIMESTAMP>();
          auto weight_qty = pow(0.5, count_sell);
          weight_ask_qty_list.push(weight_qty);
          // auto sum = compute::sum(weight_ask_qty_list);
          sum_sell += weight_qty;
          auto weight_num = pow(0.5, count_sell);
          sum_weight_sell_num_1s += weight_num;
        }
      });
    }
    sum_weight_bid_qty_list.push(sum_buy);
    sum_weight_ask_qty_list.push(sum_sell);
    // 每秒的累计加权成交量
    sum_weight_bid_qty_1s_list.push(sum_weight_buy_1s);
    sum_weight_ask_qty_1s_list.push(sum_weight_sell_1s);
    // 每秒的累计加权计数
    sum_weight_bid_num_1s_list.push(sum_weight_buy_num_1s);
    sum_weight_ask_num_1s_list.push(sum_weight_sell_num_1s);
    sum_time_weight_ask_amt_1s_list.push(count_sell_1s > 0 ? time_weight_amt / count_sell_1s : 0.0);

    trade_act_buy_qty_list.push(act_buy_qty);
    trade_act_sell_qty_list.push(act_sell_qty);

    trade_act_buy_num_list.push(act_buy_num);
    trade_act_sell_num_list.push(act_sell_num);

    trade_price_num_list.push(active_over_b1_num);
    trade_price_num_ob1_list.push(active_over_b1_num);

    trade_sell_consum_list.push(over_last_1s_s1_buy_qty);
    trade_buy_consum_list.push(over_last_1s_b1_sell_qty);

    total_ask_amount_list.push(total_sell_amount);
    total_bid_amount_list.push(total_buy_amount);
    total_ask_qty_list.push(total_sell_qty);
    total_bid_qty_list.push(total_buy_qty);

  } else {
    if (quote_price_bid1_list.size() > 0)
      quote_price_bid1_list.push(quote_price_bid1_list.back());
    else
      quote_price_bid1_list.push(0.0);
    trade_price_num_list.push(0);
  }

  return Status::OK();
}
} // namespace huatai::atsquant::factor
