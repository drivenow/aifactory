import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import polars as pl
import os
from AIQuant.datamanager import DataManager
from xquant.setXquantEnv import xquantEnv
from xquant.thirdpartydata.factordata import FactorData as TFactorData
from xquant.thirdpartydata.fic_api_data import FicApiData
from AIQuant.indicator.index_platform_data import IndicatorData


class TestDataManager:
    
    @pytest.fixture
    def data_manager(self):
        """创建DataManager实例"""
        return DataManager()
    
    @pytest.fixture
    def mock_conf(self):
        """创建配置mock对象"""
        conf = MagicMock(spec=DataManager)
        return conf

    def test_get_data_with_table_and_fields(self, data_manager, mock_conf):
        """
        测试LIB_ID存在且类型为table，有指定查询字段的情况
        mock对象：is_valid_date, split_date_by_month, os.path.exists, pl.scan_parquet
        mock返回值：日期验证通过，月份分割结果，文件存在，模拟DataFrame数据
        预期输出：返回包含指定字段的DataFrame
        """
        # 设置conf参数
        # 设置LIB_ID为ASHAREEODPRICES
        mock_conf.LIB_ID = "ASHAREEODPRICES"
        # 设置API开始日期
        mock_conf.API_START = "19910102"
        # 设置API结束日期
        mock_conf.API_END = "19910131"
        # 设置LIB_TYPE为table类型
        mock_conf.LIB_TYPE = "table"
        # 根据环境变量判断使用哪个路径
        if xquantEnv == 0:
            mock_conf.TABLE_BASE_PATH = '/data/user/quanttest007/library_alpha/quant_data/SOURCE_TABLES'
            mock_conf.FACTOR_BASE_PATH = '/data/user/quanttest007/library_alpha/quant_data/daily_factor'
        else:
            mock_conf.TABLE_BASE_PATH = '/dfs/group/800657/library_alpha/quant_data/table/' 
            mock_conf.FACTOR_BASE_PATH = '/dfs/group/800657/library_alpha/quant_data/factor/daily_factor/'
        # 设置需要查询的字段列表
        mock_conf.LIB_ID_FEILD = ["S_DQ_PRECLOSE", "S_DQ_OPEN"]
        mock_conf.API_TYPE = None
        result = data_manager.get_data(mock_conf)
        print(result)
        assert "S_DQ_PRECLOSE" in result.columns
        assert "S_DQ_OPEN" in result.columns
        # 返回列包含 datetime,symbol
        assert len(result.columns) == len(mock_conf.LIB_ID_FEILD) + 2



    def test_get_data_with_table_no_fields(self, data_manager, mock_conf):
        """
        测试LIB_ID存在且类型为table，无指定查询字段的情况
        mock对象：is_valid_date, split_date_by_month, os.path.exists, pl.scan_parquet
        mock返回值：日期验证通过，月份分割结果，文件存在，模拟DataFrame数据
        预期输出：返回所有字段的DataFrame
        """
        # 设置LIB_ID
        mock_conf.LIB_ID = "ASHAREEODPRICES"  
        # 设置API开始日期
        mock_conf.API_START = "19910102"      
        # 设置API结束日期
        mock_conf.API_END = "19910131"
        # 设置LIB_TYPE为table类型        
        mock_conf.LIB_TYPE = "table"          
        # 判断环境变量是否为0
        if xquantEnv == 0:                    
            mock_conf.TABLE_BASE_PATH = '/data/user/quanttest007/library_alpha/quant_data/SOURCE_TABLES'  # 设置表路径（环境0）
            mock_conf.FACTOR_BASE_PATH = '/data/user/quanttest007/library_alpha/quant_data/daily_factor'  # 设置因子路径（环境0）
        else:                                 # 否则使用其他路径
            mock_conf.TABLE_BASE_PATH = '/dfs/group/800657/library_alpha/quant_data/table/'               # 设置表路径（环境非0）
            mock_conf.FACTOR_BASE_PATH = '/dfs/group/800657/library_alpha/quant_data/factor/daily_factor/' # 设置因子路径（环境非0）
        # 清空字段配置项，表示不指定具体字段
        mock_conf.LIB_ID_FEILD = ''           
        # 设置API类型为空
        mock_conf.API_TYPE = None             

        # patch的return_value会替换该语句或方法的结果
        with patch.object(DataManager, 'is_valid_date', return_value=True) as mock_valid, \
             patch.object(DataManager, 'split_date_by_month', return_value={'199101':['19910102','19910103']}) as mock_split, \
             patch('os.path.exists', return_value=True) as mock_exists:
            #  patch('polars.scan_parquet') as mock_scan:
            
            # # 创建真实的polars DataFrame
            # mock_df = pl.DataFrame({
            #     "datetime": ["19910102", "19910103"],
            #     "symbol": ["600653.SH", "600651.SH"],
            #     "close": [150.0, 160.0]
            # })
            
            # mock_lazy_df = mock_df.lazy()
            # mock_scan.return_value = mock_lazy_df

            # 调用get_data方法获取数据
            result = data_manager.get_data(mock_conf) 
            # 打印结果用于调试 
            print(result)                              
            # 验证mock调用
            # 断言is_valid_date方法被调用
            assert mock_valid.called 
            # 断言split_date_by_month方法被调用                  
            assert mock_split.called            
            # 断言os.path.exists方法被调用       
            assert mock_exists.called                  
            # 断言返回结果是pandas DataFrame类型
            assert isinstance(result, pd.DataFrame) 
            # 断言返回全部数据列26列   
            assert len(result.columns) == 26 
            # 断言返回结果包含"S_DQ_ADJCLOSE"列                  
            assert "S_DQ_ADJCLOSE" in result.columns 
    
    def test_get_data_multiple_months(self, data_manager, mock_conf):
        """
        测试多个月份数据合并的情况
        mock对象：is_valid_date, split_date_by_month, os.path.exists, pl.scan_parquet
        mock返回值：多个月份的数据文件
        预期输出：返回合并后的DataFrame
        """
        mock_conf.LIB_ID = "ASHAREEODPRICES"
        mock_conf.API_START = "19910102"
        mock_conf.API_END = "19910228"
        mock_conf.LIB_TYPE = "table"
        # 判断环境变量是否为0
        if xquantEnv == 0:                    
            mock_conf.TABLE_BASE_PATH = '/data/user/quanttest007/library_alpha/quant_data/SOURCE_TABLES'  # 设置表路径（环境0）
            mock_conf.FACTOR_BASE_PATH = '/data/user/quanttest007/library_alpha/quant_data/daily_factor'  # 设置因子路径（环境0）
        else:                                 # 否则使用其他路径
            mock_conf.TABLE_BASE_PATH = '/dfs/group/800657/library_alpha/quant_data/table/'               # 设置表路径（环境非0）
            mock_conf.FACTOR_BASE_PATH = '/dfs/group/800657/library_alpha/quant_data/factor/daily_factor/' # 设置因子路径（环境非0）
        mock_conf.LIB_ID_FEILD = ''
        mock_conf.API_TYPE = ''
        df = data_manager.get_data(mock_conf)
        print(df)

        with patch.object(DataManager, 'is_valid_date', return_value=True), \
             patch.object(DataManager, 'split_date_by_month', return_value={'199101':['19910102','19910103'],'199102':['19910201','19910204']}), \
             patch('os.path.exists', return_value=True), \
             patch('polars.scan_parquet') as mock_scan:
            
            # 创建两个月的测试数据
            jan_df = pl.DataFrame({
                "datetime": ["19910102", "19910103"],
                "symbol": ["600651.SH", "600653.SH"],
                "S_DQ_OPEN": [150.0, 160.0]
            })
            
            feb_df = pl.DataFrame({
                "datetime": ["19910201", "19910204"],
                "symbol": ["600651.SH", "600653.SH"],
                "S_DQ_OPEN": [155.0, 165.0]
            })
            
            # 模拟多个文件返回不同的数据
            def side_effect(file_path):
                if "199101" in file_path:
                    return jan_df.lazy()
                elif "199102" in file_path:
                    return feb_df.lazy()
                return pl.DataFrame().lazy()
            
            mock_scan.side_effect = side_effect

            result = data_manager.get_data(mock_conf)
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 4  # 两个月份的数据合并
            print(result)
            assert all(date in result['datetime'].values for date in ['19910102', '19910103', '19910201', '19910204'])

    def test_get_data_no_cache_files(self, data_manager, mock_conf):
        """
        测试LIB_ID存在但无缓存文件的情况
        mock对象：is_valid_date, split_date_by_month, os.path.exists
        mock返回值：日期验证通过，月份分割结果，文件不存在
        预期输出：返回空的DataFrame
        """
        mock_conf.LIB_ID = "ASHAREEODPRICES"
        mock_conf.API_START = "19910502"
        mock_conf.API_END = "19910503"
        mock_conf.LIB_TYPE = "table"
        # 判断环境变量是否为0
        if xquantEnv == 0:                    
            mock_conf.TABLE_BASE_PATH = '/data/user/quanttest007/library_alpha/quant_data/SOURCE_TABLES'  # 设置表路径（环境0）
            mock_conf.FACTOR_BASE_PATH = '/data/user/quanttest007/library_alpha/quant_data/daily_factor'  # 设置因子路径（环境0）
        else:                                 # 否则使用其他路径
            mock_conf.TABLE_BASE_PATH = '/dfs/group/800657/library_alpha/quant_data/table/'               # 设置表路径（环境非0）
            mock_conf.FACTOR_BASE_PATH = '/dfs/group/800657/library_alpha/quant_data/factor/daily_factor/' # 设置因子路径（环境非0）
        mock_conf.LIB_ID_FEILD = None
        mock_conf.API_TYPE = None

        with patch.object(DataManager, 'is_valid_date', return_value=True), \
             patch.object(DataManager, 'split_date_by_month', return_value=["199105"]), \
             patch('os.path.exists', return_value=False):

            result = data_manager.get_data(mock_conf)
            
            assert isinstance(result, pd.DataFrame)
            assert result.empty

    def test_get_data_with_wind_api(self, data_manager, mock_conf):
        """
        测试API_TYPE为wind的情况
        mock对象：tfd.get_factor_value
        mock返回值：模拟因子数据DataFrame
        预期输出：返回API获取的DataFrame
        """
        mock_conf.LIB_ID = ''
        mock_conf.API_TYPE = "wind"
        mock_conf.API_KWARGS={"library_name": "WIND_ASHAREEODPRICES", "OPDATE": [">=20020724", "<=20020725"]}
        df = data_manager.get_data(mock_conf)
        print(df)

        with patch.object(TFactorData, 'get_factor_value') as mock_wind:
            mock_wind.return_value = pd.DataFrame({"trade_dt": ["19910610"], "S_DQ_PRECLOSE": [368.20]})
            
            result = data_manager.get_data(mock_conf)
            # print(mock_wind.call_args_list)
            mock_wind.assert_called_with(library_name="WIND_ASHAREEODPRICES", OPDATE=['>=20020724', '<=20020725'])
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 1

    def test_get_data_with_zx_api(self, data_manager, mock_conf):
        """
        测试API_TYPE为zx的情况
        mock对象：fic.get_fic_api_data
        mock返回值：模拟API响应数据
        预期输出：返回API数据的data字段
        """
        mock_conf.LIB_ID = ''
        mock_conf.API_TYPE = "zx"
        mock_conf.API_KWARGS = {
                            "resource": "ZX_STKDEPTTRADINFO", 
                            "paramMaps": {"LISTDATE": "20251113"}
                            }
        df = data_manager.get_data(mock_conf)
        print(df)

        with patch.object(FicApiData,'get_fic_api_data') as mock_zx:
            mock_zx.return_value = {"data": pd.DataFrame({"col1": [1, 2]})}
            
            result = data_manager.get_data(mock_conf)
            
            mock_zx.assert_called_with(resource="ZX_STKDEPTTRADINFO", paramMaps={"LISTDATE": "20251113"})
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2

    def test_get_data_with_indicator_api(self, data_manager, mock_conf):
        """
        测试API_TYPE为indicator的情况
        mock对象：ida.get_indicator_data
        mock返回值：模拟指标数据
        预期输出：返回指标数据DataFrame
        """
        mock_conf.LIB_ID = None
        mock_conf.API_TYPE = "indicator"
        mock_conf.API_KWARGS={
                            "date": "20251114",
                            "action": "27720",
                            "props": "10035|10049|10055|10041|10042|10043|10044|11|10036|10018",
                            "marketType": "HSJASH"
                            }
        df = data_manager.get_data(mock_conf)
        print(df)

        with patch.object(IndicatorData,'get_indicator_data') as mock_indicator:
            mock_indicator.return_value = pd.DataFrame({"indicator": [1.0, 2.0]})
            
            result = data_manager.get_data(mock_conf)
            
            # 验证过滤掉library_name参数
            mock_indicator.assert_called_with(date="20251114",
                                              action="27720",
                                              props= "10035|10049|10055|10041|10042|10043|10044|11|10036|10018",
                                              marketType= "HSJASH")
            assert isinstance(result, pd.DataFrame)

    def test_get_data_with_indicator_min_api_with_codes(self, data_manager, mock_conf):
        """
        测试API_TYPE为indicator_min且有codes参数的情况
        mock对象：ida.get_min_indicator_data
        mock返回值：模拟分钟指标数据
        预期输出：返回分钟指标数据DataFrame
        """
        mock_conf.LIB_ID = ''
        mock_conf.API_TYPE = "indicator_min"
        mock_conf.API_KWARGS = {"date": "20251128",
                            "action": "27720",
                            "props": "10023",
                            "marketType": "HSJASH",
                            "codes": "600519|1_0"}
        df = data_manager.get_data(mock_conf)
        print(df)

        with patch.object(IndicatorData, 'get_min_indicator_data') as mock_min_indicator:
            mock_min_indicator.return_value = pd.DataFrame({"min_data": [1, 2]})
            
            result = data_manager.get_data(mock_conf)
            
            mock_min_indicator.assert_called_with(codes="600519|1_0",
                                                  date="20251128",
                                                  action= "27720",
                                                  props= "10023",
                                                  marketType= "HSJASH"
                                                  )
            assert isinstance(result, pd.DataFrame)
    def test_get_data_with_indicator_min_api_no_codes(self, data_manager, mock_conf):
            """
            测试API_TYPE为indicator_min且无codes参数的情况
            mock对象：ida.get_min_indicator_data
            mock返回值：模拟全量分钟指标数据
            预期输出：返回全量分钟指标数据DataFrame
            """
            mock_conf.LIB_ID = ""
            mock_conf.API_TYPE = "indicator_min"
            mock_conf.API_KWARGS = {"date": "20251128",
                                "action": "27720",
                                "props": "10023",
                                "marketType": "HSJASH"
                                }
            
            df = data_manager.get_data(mock_conf)
            print(df)
            

            with patch.object(IndicatorData, 'get_min_indicator_data') as mock_min_indicator:
                mock_min_indicator.return_value = pd.DataFrame({"all_data": [1, 2, 3]})
                
                result = data_manager.get_data(mock_conf)
                print(mock_min_indicator.call_args_list)
                mock_min_indicator.assert_called_with(stock_all=True,
                                                    date="20251128",
                                                    action= "27720",
                                                    props= "10023",
                                                    marketType= "HSJASH"
                                                    )
                assert isinstance(result, pd.DataFrame)

    def test_get_data_invalid_date_assertion(self, data_manager, mock_conf):
        """
        测试日期验证失败的情况
        mock对象：is_valid_date
        mock返回值：返回False触发断言
        预期输出：抛出AssertionError
        """
        mock_conf.LIB_ID = "ASHAREEODPRICES"
        mock_conf.API_START = "invalid_date"
        mock_conf.API_END = "19910131"

        with patch.object(DataManager, 'is_valid_date', return_value=False):
            with pytest.raises(AssertionError):
                print("AssertionError")
                data_manager.get_data(mock_conf)
    

if __name__ == "__main__":
    pytest.main([__file__, "-vs"])