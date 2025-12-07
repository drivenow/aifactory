from __future__ import annotations

from typing import Dict, Any, Tuple

from .tools.mock_factor_tool import (
    render_factor_code,
    simple_factor_body_from_spec,
)

from domain.codegen.agent import invoke_l3_agent, invoke_l3_cpp_agent
from domain.codegen.view import CodeGenView, CodeMode, DryrunResult, SemanticCheckResult
from domain.codegen.semantic import check_semantics_static, check_semantics_agent
from domain.codegen.runner import run_factor


def generate_l3_factor_code(view: CodeGenView) -> str:
    return invoke_l3_agent(view)


def generate_l3_cpp_factor_code(view: CodeGenView) -> str:
    return invoke_l3_cpp_agent(view)


def generate_factor_code_from_spec(state, check_static_round = 3, check_agent_round = 3) -> str:
    """生成因子代码（兼容旧接口），内部执行完整语义守护流程并返回代码字符串。"""
    res = generate_factor_with_semantic_guard(state, check_static_round, check_agent_round)
    return res.get("factor_code", "")


def generate_factor_with_semantic_guard(state, check_static_round = 1, check_agent_round = 3) -> Dict[str, Any]:
    """完整工作流：生成→静态语义检查(失败可重试)→dryrun→agent 语义检查(最多 check_agent_round 轮)。"""
    working_state: Dict[str, Any] = dict(state) if isinstance(state, dict) else {}
    static_passed = False
    static_detail: Dict[str, Any] = {}
    code = ""

    # 只校验一次静态语义，传给后面的语义大模型进行校验
    for gen_round in range(check_static_round):
        view = CodeGenView.from_state(working_state)
        if view.code_mode == CodeMode.L3_PY or view.code_mode == "l3_py":
            code = generate_l3_factor_code(view)
        elif view.code_mode == CodeMode.L3_CPP or view.code_mode == "l3_cpp":
            code = generate_l3_cpp_factor_code(view)
        else:
            body = simple_factor_body_from_spec(view.user_spec)
            code = render_factor_code(view.factor_name, view.user_spec, body)

        tmp_state = {**working_state, "factor_code": code}
        static_passed, static_detail = check_semantics_static(tmp_state)



    # 准备运行 dryrun
    # 把失败的静态语义信息回灌给下一轮生成，便于模型修正
    working_state["check_semantics"] = static_detail
    working_state["factor_code"] = code
    dryrun_raw = run_factor(working_state)
    dryrun_result = _normalize_dryrun_output(dryrun_raw)

    # 语义 agent 最多 check_agent_round 轮
    agent_attempts = 0
    agent_passed = False
    agent_detail: Dict[str, Any] = {}
    while agent_attempts < check_agent_round:
        tmp_state = {
            **working_state,
            "factor_code": code,
            "dryrun_result": dryrun_result.model_dump(),
            "check_semantics": static_detail,
            "semantic_agent_attempts": agent_attempts,
        }
        agent_passed, agent_detail = check_semantics_agent(tmp_state)
        if agent_passed:
            break
        agent_attempts += 1

    update = {
        "factor_code": code,
        "check_semantics": agent_detail if agent_detail else static_detail,
        "dryrun_result": dryrun_result.model_dump(),
        "semantic_agent_attempts": agent_attempts,
    }

    if isinstance(state, dict):
        state.update(update)

    return update


def _normalize_dryrun_output(run_res: Dict[str, Any]) -> DryrunResult:
    return DryrunResult(
        success=bool(run_res.get("success")),
        stdout=None if run_res.get("stdout") is None else str(run_res.get("stdout")),
        stderr=None if run_res.get("stderr") is None else str(run_res.get("stderr")),
    )



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
