import json
import random
from xquant.setXquantEnv import xquantEnv
from xquant.factordata import FactorData
import pandas as pd
import requests
import datetime as dt


class IndicatorData:
    def __init__(self):
        if xquantEnv == 1:
            ip = random.choice(['10.7.9.89', '168.15.10.79'])
        else:
            ip = '168.64.37.187'
        self.url = f"http://{ip}:10000/ormp/groovy/common/GeneralService/queryIndicatorWithFilter"
        self.fd = FactorData()
        self.stock_pool = None

    def __set_stock_pool(self, date):
        if not self.stock_pool:
            stock_alla = self.fd.hset('MARKET', date, 'ALLA')['stock'].to_list()
            stock_bj = self.fd.hset('MARKET', date, 'BJ')['stock'].to_list()
            self.stock_pool = list(set(stock_alla + stock_bj))
            self.stock_pool = [i.split(".")[0] for i in self.stock_pool]

    def get_symbol(self, ticker_num):
        ticker_num = str(ticker_num)
        ticker = ticker_num.zfill(6)
        if ticker.startswith("6") or ticker.startswith("900"):
            suffix = ".SH"
        elif ticker.startswith("0") or ticker.startswith("3") or ticker.startswith("2"):
            suffix = ".SZ"
        elif ticker.startswith("8") or ticker.startswith("9") or ticker.startswith("43"):
            suffix = ".BJ"
        else:
            suffix = ""
        ticker = ticker + suffix
        return ticker

    def is_valid_date(self, check_date):
        try:
            if isinstance(check_date, int):
                check_date = str(check_date)
            assert len(check_date) == 8
            dt.datetime.strptime(check_date, '%Y%m%d')
            return True
        except Exception as e:
            print("日期-{0}的格式有误，请传入正确格式如'20200201'".format(check_date))
            return False

    def __get_indicator_data(self, **kwargs):
        resp = None
        try:
            resp = requests.get(self.url, params=kwargs, timeout=60)
            res = json.loads(resp.text)
        except Exception as e:
            print(f' 请求 {self.url} 异常: {str(e)} \n {resp.text if resp else str(e)}')
            return pd.DataFrame()
        if str(res['code']) != "0":
            print(f'请求 {self.url} 异常: {resp.text}')
            return pd.DataFrame()
        df_data = pd.json_normalize(res['resultData'], sep='_')
        if len(df_data) > 0:
            result_df = df_data.assign(
                            SecurityId=lambda _df: _df['SecurityId'].apply(self.get_symbol),
                            TradeDate=lambda _df: _df['TradeDate'].astype(str),
                                    )
            if "date" in kwargs:
                result_df["TradeDate"] = kwargs["date"]
            return result_df
        else:
            return df_data

    def get_indicator_data(self, **kwargs) -> pd.DataFrame:
        return self.__get_indicator_data(**kwargs)

    def get_min_indicator_data(self, stock_all=False, **kwargs):
        if stock_all:
            if "date" in kwargs:
                date = kwargs["date"]
            else:
                date = dt.datetime.now().strftime("%Y%m%d")
            self.__set_stock_pool(date=date)
            df_list = []
            for stock in self.stock_pool:
                kwargs["codes"] = f"{stock}|1_0"
                df_1 = self.__get_indicator_data(**kwargs)
                try:
                    SecurityId = df_1.iloc[0]["SecurityId"]
                    Market = df_1.iloc[0]["Market"]
                    TradeDate = df_1.iloc[0]["TradeDate"]
                    data = df_1.iloc[0]["ZJLX1m"]
                    if data:
                        df_p = pd.DataFrame(data)
                        df_p["SecurityId"] = SecurityId
                        df_p["Market"] = Market
                        df_p["TradeDate"] = TradeDate
                        df_list.append(df_p)
                except:
                    continue
            if df_list:
                df = pd.concat(df_list, ignore_index=True)
            else:
                df = pd.DataFrame()
        else:
            df_1 = self.__get_indicator_data(**kwargs)
            if len(df_1) > 0:
                SecurityId = df_1.iloc[0]["SecurityId"]
                Market = df_1.iloc[0]["Market"]
                TradeDate = df_1.iloc[0]["TradeDate"]
                data = df_1.iloc[0]["ZJLX1m"]
                if data:
                    df = pd.DataFrame(data)
                    df["SecurityId"] = SecurityId
                    df["Market"] = Market
                    df["TradeDate"] = TradeDate
                else:
                    df = pd.DataFrame()
            else:
                df = pd.DataFrame()
        return df


if __name__ == '__main__':
    ida = IndicatorData()
    # args = {'action': '27720',
    #         'props': '10035|10049|10055|10041|10042|10043|10044|11|10036|10018|10086|40105|40031|40002|10014|10015|10008|70098|70391|40624|10016|10017|10020|79999',
    #         'marketType': 'HSJASH',
    #         'date': '20251114'
    #         }
    args = {'action': '27720',
            'props': '10023',
            'marketType': 'HSJASH',
            'date': '20251124',
            'codes': '600519|1_0'
            }
    # df = ida.get_indicator_data(action='27720', props='10035|10049|10055|10041|10042', marketType='HSJASH',date= '20251114')
    # df = ida.get_indicator_data(**args)
    # print(df)

    df_res = ida.get_min_indicator_data(stock_all=True, **args)
    print(df_res)
