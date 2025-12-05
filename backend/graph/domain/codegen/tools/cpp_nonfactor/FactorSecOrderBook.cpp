#include "huatai/atsquant/factor/SAMPLE_1S/nonfactor/FactorSecOrderBook.h"
#include "huatai/atsquant/factor/schema.h"

namespace huatai::atsquant::factor {

void FactorSecOrderBook::on_init() { set_sample_mode(false); }

Status FactorSecOrderBook::calculate() {
  auto sample_1s_flag = get_sample_flag();
  if (!sample_1s_flag && get_factor_manager_param().calculate_mode == FactorManagerParam::CalculateMode::SAMPLE_1S) {
    value() = 0;
    return Status::OK();
  }

  // 获取上一秒最后一根盘口数据
  auto quotes = get_market_data().get_prev_n_quote(1);
  auto last_quote = quotes[0];
  auto seq_no = quotes[-1].item<QuoteSchema::Index::TRIGGER_APPL_SEQ_NUM>();
  auto last_seq_no = last_quote.item<QuoteSchema::Index::TRIGGER_APPL_SEQ_NUM>();
  auto last_time = quotes[-1].item<QuoteSchema::Index::TRIGGER_TIME>();

  // 获取采样的时间戳，为上一秒的整秒+1秒
  auto sec_mdtime = (last_quote.item<QuoteSchema::Index::TRIGGER_TIME>() - 1) / 1000 * 1000 + 1000L;
  if (trigger_time_list.size() != 0 and sec_mdtime <= trigger_time_list.back()) {
    sec_mdtime = trigger_time_list.back() + 1000L;
  }
  trigger_time_list.push(sec_mdtime); // 这一整秒的最后一条
  if (open_px_list.size() == 0 || open_px_list.back() < 1e-6) {
    auto first_quote = get_market_data().get_prev_n_quote(100000)[open_px_list.size()];
    if (first_quote.item<QuoteSchema::Index::TOTAL_VOLUME>() > 0) {
      open_px_list.push(std::round(first_quote.item<QuoteSchema::Index::TOTAL_TURNOVER>() /
                                   first_quote.item<QuoteSchema::Index::TOTAL_VOLUME>() * 100) /
                        100);
    } else {
      open_px_list.push(0.0);
    }
  } else {
    open_px_list.push(open_px_list.back());
  }
  auto ask1_px = 0.0;
  auto bid1_px = 0.0;
  auto mid_px = 0.0;
  ask1_px = last_quote.list_item<QuoteSchema::Index::ASK_PRICE>()[0];
  bid1_px = last_quote.list_item<QuoteSchema::Index::BID_PRICE>()[0];
  mid_px = (ask1_px + bid1_px) / 2.0;
  auto mid_up_flag = 0.0;
  if (mid_px_list.size() > 0)
    mid_up_flag = mid_px > mid_px_list.back() ? 1.0 : 0.0;
  mid_px_list.push(mid_px);
  mid_px_up_flag_list.push(mid_up_flag);
  last_px_list.push(last_quote.item<QuoteSchema::Index::LAST_PX>());
  high_px_list.push(last_quote.item<QuoteSchema::Index::HIGH_PX>());
  low_px_list.push(last_quote.item<QuoteSchema::Index::LOW_PX>());
  total_volume_list.push(last_quote.item<QuoteSchema::Index::TOTAL_VOLUME>());
  total_turnover_list.push(last_quote.item<QuoteSchema::Index::TOTAL_TURNOVER>());
  total_ask_qty_list.push(last_quote.item<QuoteSchema::Index::TOTAL_ASK_QTY>());
  total_bid_qty_list.push(last_quote.item<QuoteSchema::Index::TOTAL_BID_QTY>());
  if (last_quote.item<QuoteSchema::Index::TOTAL_ASK_QTY>() > 1e-4) {
    avg_ask_price_list.push(last_quote.item<QuoteSchema::Index::AVG_SELL_PRICE>());
  } else {
    avg_ask_price_list.push(0.0);
  }
  if (last_quote.item<QuoteSchema::Index::TOTAL_BID_QTY>() > 1e-4) {
    avg_bid_price_list.push(last_quote.item<QuoteSchema::Index::AVG_BUY_PRICE>());
  } else {
    avg_bid_price_list.push(0.0);
  }
  trades_list.push(last_quote.item<QuoteSchema::Index::TRADES>());
  trigger_appl_seq_num_list.push(seq_no);
  // 档位字段
  auto ask_qty = last_quote.list_item<QuoteSchema::Index::ASK_QTY>();
  auto bid_qty = last_quote.list_item<QuoteSchema::Index::BID_QTY>();
  auto ask_price = last_quote.list_item<QuoteSchema::Index::ASK_PRICE>();
  auto bid_price = last_quote.list_item<QuoteSchema::Index::BID_PRICE>();
  bid_qty_list.push(bid_qty);
  bid_price_list.push(bid_price);
  bid_order_nums_list.push(last_quote.list_item<QuoteSchema::Index::BID_ORDER_NUMS>());
  ask_qty_list.push(ask_qty);
  ask_price_list.push(ask_price);
  ask_order_nums_list.push(last_quote.list_item<QuoteSchema::Index::ASK_ORDER_NUMS>());
  double *ask_amt = new double[10];
  double *bid_amt = new double[10];
  for (int i = 0; i < 10; i++) {
    ask_amt[i] = ask_qty[i] * ask_price[i];
    bid_amt[i] = bid_qty[i] * bid_price[i];
  }
  ask_amt_list.push(ask_amt);
  bid_amt_list.push(bid_amt);

  value() = sec_mdtime;
  return Status::OK();
}

} // namespace huatai::atsquant::factor
