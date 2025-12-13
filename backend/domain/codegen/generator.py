from __future__ import annotations

from typing import Dict, Any, Tuple
from domain.codegen.framework.factor_mock_tool import (
    render_factor_code,
    simple_factor_body_from_spec,
)

from domain.codegen.agent_with_prompt import (
    agent_factor_l3_cpp,
    agent_factor_l3_py,
    agent_factor_rayframe_py,
)
from domain.codegen.view import CodeGenView, CodeMode, DryrunResult, SemanticCheckResult
from domain.codegen.semantic import check_semantics_static, check_semantics_agent
from domain.codegen.runner import run_factor
from domain.logger import domain_logger


def generate_l3_factor_code(view: CodeGenView) -> str:
    return agent_factor_l3_py.invoke_l3_agent(view)


def generate_l3_cpp_factor_code(view: CodeGenView) -> str:
    return agent_factor_l3_cpp.invoke_l3_cpp_agent(view)


def generate_rayframe_factor_code(view: CodeGenView) -> str:
    return agent_factor_rayframe_py.invoke_rayframe_agent(view)


def generate_factor_with_semantic_guard(state: CodeGenView | FactorAgentState, check_agent_round = 3) -> CodeGenView:
    """
    完整工作流：生成→静态语义检查(失败可重试)→dryrun→agent 语义检查(最多 check_agent_round 轮)。

    参数
    ----
    state : FactorAgentState
        包含因子名称、因子规格、代码模式等信息的完整状态对象。
    check_agent_round : int, optional
        agent 语义检查轮数，默认 3 轮。

    返回
    ----
    Dict[str, Any]
        包含因子代码、静态语义检查结果、dryrun 结果、agent 语义检查结果等信息的更新状态字典。
    """
    view: CodeGenView = CodeGenView.from_state(state)
    # 语义 agent 最多 check_agent_round 轮，失败则带着静态+运行信息重生成代码
    agent_attempts = 0
    agent_passed = False
    agent_detail: Dict[str, Any] = {}
    while agent_attempts < check_agent_round:
        # （1）生成代码并做静态语义校验
        view = _generate_with_static(view)
        # （2）调用 agent 检查语义
        semantic_passed, semantic_detail = check_semantics_agent(view)
        view.set_semantic_check_result(semantic_detail)
        # （3）重新跑 dryrun
        dryrun_result = run_factor(view)
        # （4）更新 view 里的 dryrun 结果
        view.set_dryrun_result(dryrun_result)

        # 打印美观的分隔符
        domain_logger.info(f"\n{str(view)}")
        
        if view.check_semantics.passed and view.dryrun_result.success:
             # 成功后，将代码持久化到文件（如果指定了 factor_path 或默认路径）
            try:
                saved_path = view.save_code_to_file()
                domain_logger.info(f"Factor code saved to: {saved_path}")
            except Exception as e:
                domain_logger.warning(f"Failed to save factor code: {e}")
            break
            
        agent_attempts += 1

    return view


def _generate_with_static(state: CodeGenView | FactorAgentState) -> CodeGenView:
    """调用代码生成 agent，并做静态语义校验，失败信息回灌到 working_state 里供下一轮提示。"""
    static_detail: Dict[str, Any] = {}
    code = ""
    view = CodeGenView.from_state(state)
    if view.code_mode == CodeMode.L3_PY or view.code_mode == "l3_py":
        code = generate_l3_factor_code(view)
    elif view.code_mode == CodeMode.L3_CPP or view.code_mode == "l3_cpp":
        code = generate_l3_cpp_factor_code(view)
    elif view.code_mode == CodeMode.RAYFRAME_PY or view.code_mode == "rayframe_py":
        code = generate_rayframe_factor_code(view)
    else:
        body = simple_factor_body_from_spec(view.user_spec)
        code = render_factor_code(view.factor_name, view.user_spec, body)

    # （1）更新 view 里的 factor_code
    view.factor_code = code
    static_passed, static_detail = check_semantics_static(view)
    # （2）更新 view 里的静态语义检查结果
    view.set_semantic_check_result(static_detail)
    # 准备运行 dryrun
    dryrun_result = run_factor(view)
    # （3）更新 view 里的 dryrun 结果
    view.set_dryrun_result(dryrun_result)
    return view




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
        domain_logger.info(code)
    else:
        view = CodeGenView(
            factor_name="TestFactor",
            user_spec="计算股票的简单移动平均线",
            code_mode=CodeMode.L3_PY,
        )
        code = generate_l3_factor_code(view)
        domain_logger.info(code)
