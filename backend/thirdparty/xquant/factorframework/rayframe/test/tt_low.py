import sys
sys.path.append("/tmp/pycharm_project_572/xquant/factorframework/rayframe/test/")

from xquant.factorframework.rayframe.calculation.DataCalculation import run_securities_days

res = run_securities_days(factor_list=['ZG_factors'], security_list=['688001.SH'],
                          data_input_mode=['TICK_RAW', 'TRANSACTION_RAW','KLINE1M_RAW'], security_type='stock', library_name='test_low1',
                          start_date='20200602', end_date='20200609',
                          return_mode='show', file_path='./', num_cpus=3)#, options={'local_mode': True}
print(res)


