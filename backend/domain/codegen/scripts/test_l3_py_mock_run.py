import sys
import os
import pathlib

# Add the project root to the python path
ROOT = pathlib.Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from domain.framework.factor_l3_py_tool import l3_mock_run

# Sample L3 Factor Code (Mocking a simple factor)
SAMPLE_L3_CODE = """
import numpy as np
from L3FactorFrame.FactorBase import FactorBase

class FactorTestFactor(FactorBase):
    def __init__(self, config, factorManager, marketDataManager):
        super().__init__(config, factorManager, marketDataManager)
        self.window = config.get('window', 20)  # 默认20秒窗口
        self.nonfactor_ob = self.get_factor_instance("FactorSecOrderBook")
        self.price_window = []  # 缓存价格序列
        
    def calculate(self):
        # 获取最新价格
        if len(self.nonfactor_ob.last_px_list) > 0:
            current_price = self.nonfactor_ob.last_px_list[-1]
            self.price_window.append(current_price)
            print(current_price)
            
            # 维护窗口长度
            if len(self.price_window) > self.window:
                self.price_window.pop(0)
                
            # 计算SMA (简单移动平均)
            n = len(self.price_window)
            sma = np.mean(self.price_window) if n > 0 else 0.0
            self.addFactorValue(sma)
        else:
            self.addFactorValue(0.0)
"""

def main():
    print("Running L3 Factor Mock Test...")
    print("-" * 30)
    print("Input Code:")
    print(SAMPLE_L3_CODE)
    print("-" * 30)
    
    result = l3_mock_run.invoke(SAMPLE_L3_CODE)
    
    print("Result:")
    print(result)
    
    if result.get("ok"):
        print("\nSUCCESS: Factor executed successfully.")
        print("Calculated Values:", result.get("result"))
    else:
        print("\nFAILURE: Factor execution failed.")
        print("Error:", result.get("state_error"))

if __name__ == "__main__":
    main()
