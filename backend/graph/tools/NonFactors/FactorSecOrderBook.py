import numpy as np
from L3FactorFrame.FactorBase import FactorBase
from L3FactorFrame.tools.DecimalUtil import isEqual, notEqual
from L3FactorFrame.tools.helper_functions import trade_field_agg
from datetime import datetime, timedelta


class FactorSecOrderBook(FactorBase):
    def __init__(self, config, factorManager, marketDataManager):
        super().__init__(config, factorManager, marketDataManager)
        
        self.lag = 120                     
        self.last_px_list = []       
        self.high_px_list = []       
        self.low_px_list = []
        self.open_px_list = []        
        self.total_volume_list = []  
        self.total_turnover_list = []
        # self.total_ask_qty_list = [] 
        # self.total_bid_qty_list = [] 
        self.trades_list = []        
        self.trigger_appl_seq_num_list= []
        self.trigger_time_list = []  
        self.bid_qty_list = []       
        self.bid_price_list = []     
        self.bid_order_nums_list = []
        self.ask_qty_list = []       
        self.ask_price_list = []     
        self.ask_order_nums_list = []
        



    def calculate(self):
        sample_1s_flag = self.get_sample_1s_flag()
        if not sample_1s_flag and self.factorManager.mode == "SAMPLE_1S":
            self.addFactorValue(None)
            return
        
        if len(self.open_px_list)==0 or self.open_px_list[-1]<1e-4:
            if self.getPrevNTick("TotalVolume", 100000)[len(self.open_px_list)]>0:
                self.open_px_list.append(round(self.getPrevTick("TotalTurnOver")/ self.getPrevTick("TotalVolume")),2)      
            else:
                self.open_px_list.append(0.0)         
        else:
            self.open_px_list.append(self.open_px_list[-1])
        self.last_px_list.append(self.getPrevTick("LastPrice"))
        self.high_px_list.append(self.getPrevTick("HighPrice"))
        self.low_px_list.append(self.getPrevTick("LowPrice"))
        self.total_volume_list.append(self.getPrevTick("TotalVolume"))
        self.total_turnover_list.append(self.getPrevTick("TotalTurnOver"))
        # self.total_ask_qty_list.append(self.total_ask_qty_list[-1])
        # self.total_bid_qty_list.append(self.total_bid_qty_list[-1])
        self.trades_list.append(self.getPrevTick("TotalTradeNum"))
        self.trigger_appl_seq_num_list.append(self.getPrevTick("SeqNo"))
        self.trigger_time_list.append(int(self.get_timestamp()))
        self.bid_qty_list.append(self.getPrevTick("BidVolume"))
        self.bid_price_list.append(self.getPrevTick("BidPrice"))
        self.bid_order_nums_list.append(self.getPrevTick("BidNum"))
        self.ask_qty_list.append(self.getPrevTick("AskVolume"))
        self.ask_price_list.append(self.getPrevTick("AskPrice"))
        self.ask_order_nums_list.append(self.getPrevTick("AskNum"))
        
        sec_mdtime = datetime.fromtimestamp(int(self.get_timestamp())) # 转换成整秒
        self.addFactorValue(sec_mdtime)
