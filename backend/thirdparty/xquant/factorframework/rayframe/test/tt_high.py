import sys

sys.path.append("/tmp/pycharm_project_572/xquant/factorframework/rayframe/test/")

from xquant.factorframework.rayframe.calculation.DataCalculation import run_securities_days
from xquant.factorframework.rayframe import get_custom_factor_class
from xquant.factorframework.rayframe.util.util import get_fac_class

pxchange = get_fac_class('pxchange', './')
pxchange1 = get_custom_factor_class(pxchange, {"custom_params": {"interval_seconds": 50, "tick_interval_seconds": 3}})

res = run_securities_days(factor_list=['pxchange'], security_list=['688001.SH'],
                          data_input_mode=['TICK_RAW'], security_type='stock', library_name='test_high1',
                          start_date='20200102', end_date='20200108',
                          return_mode='show', file_path='./',options={'local_mode': True})
print(res)
print(res['688001.SH'].columns)

