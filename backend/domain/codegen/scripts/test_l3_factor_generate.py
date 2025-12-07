from domain.codegen import generate_factor_with_semantic_guard
from domain.codegen.view import CodeGenView, CodeMode

codemode = CodeMode.L3_CPP
if codemode == CodeMode.L3_CPP:
    view = CodeGenView(
        factor_name="TestFactor",
        user_spec="计算股票的简单移动平均线",
        factor_code = """
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
        
        # 维护窗口长度
        if len(self.price_window) > self.window:
            self.price_window.pop(0)
            
        # 计算SMA (简单移动平均)
        n = len(self.price_window)
        sma = np.mean(self.price_window) if n > 0 else 0.0
        self.addFactorValue(sma)
    else:
        self.addFactorValue(0.0)
        """,
        code_mode=CodeMode.L3_CPP,
    )
    result = generate_factor_with_semantic_guard(view)
    print(result)
else:
    view = CodeGenView(
        factor_name="TestFactor",
        user_spec="计算股票的简单移动平均线",
        code_mode=CodeMode.L3_PY,
    )
    result = generate_factor_with_semantic_guard(view)
    print(result)
