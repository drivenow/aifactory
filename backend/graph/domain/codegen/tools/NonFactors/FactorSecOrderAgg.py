import numpy as np
from L3FactorFrame.FactorBase import FactorBase
from L3FactorFrame.tools.DecimalUtil import isEqual, notEqual
from L3FactorFrame.tools.helper_functions import trade_field_agg


class FactorSecOrderAgg(FactorBase):
    def __init__(self, config, factorManager, marketDataManager):
        super().__init__(config, factorManager, marketDataManager)
        self.num_bids_sec_list = []
        self.num_asks_sec_list = []
        self.qty_bids_sec_list = []
        self.qty_asks_sec_list = []
        self.net_volume_sec_list = []

    def calculate(self):
        sample_1s_flag = self.get_sample_1s_flag()
        if sample_1s_flag == 1:
            # 获取上一秒的数据
            bs_flags = self.getPrevSecOrder("BSFlag", 1)
            volume = self.getPrevSecOrder("Volume", 1)

            buy_num = bs_flags[bs_flags == 1].sum()
            sell_num = bs_flags[bs_flags == 2].sum()
            buy_qty = volume[bs_flags==1].sum()
            sell_qty = volume[bs_flags==2].sum()
            net_volume = volume[bs_flags==1].sum()-volume[bs_flags==2].sum()


            self.num_bids_sec_list.append(buy_num)
            self.num_asks_sec_list.append(sell_num)
            self.qty_bids_sec_list.append(buy_qty)
            self.qty_asks_sec_list.append(sell_qty)
            self.net_volume_sec_list.append(net_volume)
        self.addFactorValue(0.0)