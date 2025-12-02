import numpy as np
import math
from L3FactorFrame.FactorBase import FactorBase
from L3FactorFrame.tools.DecimalUtil import isEqual, notEqual
from L3FactorFrame.tools.helper_functions import trade_field_agg


class FactorSecTradeAgg(FactorBase):
    def __init__(self, config, factorManager, marketDataManager):
        super().__init__(config, factorManager, marketDataManager)
        self.trade_buy_money_list = []
        self.trade_sell_money_list = []
        self.trade_buy_num_list = []
        self.trade_sell_num_list = []
        self.trade_buy_volume_list = []
        self.trade_sell_volume_list = []


    def calculate(self):
        timestamps = self.getPrevTick("Timestamp")
        sample_1s_flag = self.get_sample_1s_flag()
        if sample_1s_flag == 1:
            # sample_1s_flag表示超过这一秒的第一条数据，将end_timestamp设置为这一秒的整秒，作为右闭区间
            # timestamps向上取整为当前时间
            trade_qtys = self.getPrevSecTrade("Volume", 1, end_timestamp = math.ceil(timestamps))
            trade_moneys = self.getPrevSecTrade("Amount", 1, end_timestamp = math.ceil(timestamps))
            trade_sides = self.getPrevSecTrade("BSFlag", 1, end_timestamp = math.ceil(timestamps))

            active_buy_money, active_sell_money, active_buy_num, active_sell_num, active_buy_volume, active_sell_volume = \
                trade_field_agg(trade_qtys, trade_moneys, trade_sides)

            self.trade_buy_money_list.append(active_buy_money)
            self.trade_sell_money_list.append(active_sell_money)
            self.trade_buy_num_list.append(active_buy_num)
            self.trade_sell_num_list.append(active_sell_num)
            self.trade_buy_volume_list.append(active_buy_volume)
            self.trade_sell_volume_list.append(active_sell_volume)

        # Nonfactor的结果不用存
        self.addFactorValue(0.0)
