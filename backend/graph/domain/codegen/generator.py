from __future__ import annotations

from .tools.factor_template import (
    render_factor_code,
    simple_factor_body_from_spec,
)

from domain.codegen.agent import invoke_l3_agent, invoke_l3_cpp_agent
from domain.codegen.view import CodeGenView, CodeMode


def generate_l3_factor_code(view: CodeGenView) -> str:
    return invoke_l3_agent(view)


def generate_l3_cpp_factor_code(view: CodeGenView) -> str:
    return invoke_l3_cpp_agent(view)


def generate_factor_code_from_spec(state) -> str:
    view = CodeGenView.from_state(state)
    if view.code_mode == CodeMode.L3_PY or view.code_mode == "l3_py":
        return generate_l3_factor_code(view)
    if view.code_mode == CodeMode.L3_CPP or view.code_mode == "l3_cpp":
        return generate_l3_cpp_factor_code(view)

    body = simple_factor_body_from_spec(view.user_spec)
    return render_factor_code(view.factor_name, view.user_spec, body)



if __name__ == "__main__":
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
        code = generate_l3_cpp_factor_code(view)
        print(code)
    else:
        view = CodeGenView(
            factor_name="TestFactor",
            user_spec="计算股票的简单移动平均线",
            code_mode=CodeMode.L3_PY,
        )
        code = generate_l3_factor_code(view)
        print(code)
