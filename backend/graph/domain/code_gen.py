from __future__ import annotations

from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import Field, BaseModel

from ..state import FactorAgentState, ViewBase
from ..tools.factor_template import (
    render_factor_code,
    simple_factor_body_from_spec,
)
from ..tools.sandbox_runner import run_code
from ..config import get_llm
from ..prompts.factor_l3_py import PROMPT_FACTOR_L3_PY
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
import re

# Tools
from ..tools.l3_factor_tool import l3_syntax_check, l3_mock_run, _mock_run
from ..tools.codebase_fs_tools import read_repo_file, list_repo_dir
from ..tools.nonfactor_info import get_formatted_nonfactor_info
from ..state import FactorAgentState


class CodeMode(str, Enum):
    PANDAS = "pandas"
    L3_PY = "l3_py"


class SemanticCheckResult(BaseModel):
    passed: bool = True
    reason: List[str] = []
    last_error: Optional[str] = None


class DryrunResult(BaseModel):
    success: bool
    traceback: Optional[str] = None
    result_preview: Optional[Any] = None


class CodeGenView(ViewBase):
    user_spec: str = ""
    factor_name: str = "factor"
    factor_code: str = ""
    code_mode: CodeMode = CodeMode.PANDAS
    dryrun_result: DryrunResult = DryrunResult(success=True)
    check_semantics: SemanticCheckResult = SemanticCheckResult()

    @classmethod
    @ViewBase._wrap_from_state("CodeGenView.from_state")
    def from_state(cls, state: FactorAgentState) -> "CodeGenView":
        # helper to safe parse dict to pydantic
        def _parse_dryrun(d):
            if not d: return DryrunResult(success=True)
            return DryrunResult(**d)

        def _parse_semantic(d):
            if not d: return SemanticCheckResult()
            return SemanticCheckResult(**d)

        return cls(
            user_spec=state.get("user_spec") or "",
            factor_name=state.get("factor_name") or "factor",
            factor_code=state.get("factor_code") or "",
            dryrun_result=_parse_dryrun(state.get("dryrun_result")),
            check_semantics=_parse_semantic(state.get("check_semantics")),
            code_mode=state.get("code_mode") or CodeMode.PANDAS,
        )


_L3_AGENT = None

def _build_l3_codegen_agent():
    global _L3_AGENT
    if _L3_AGENT is not None:
        return _L3_AGENT

    llm = get_llm()
    if (not llm) or (create_react_agent is None):
        return None
    
    tools = [
        read_repo_file,
        list_repo_dir,
        l3_syntax_check,
        l3_mock_run,
    ]
    
    _L3_AGENT = create_react_agent(llm, tools=tools)
    return _L3_AGENT


def _extract_last_assistant_content(messages: List[Any]) -> str:
    """从 agent 返回的消息列表中提取最后一条 assistant 内容。"""
    for m in reversed(messages):
        role = getattr(m, "type", None) or getattr(m, "role", None)
        if role in ("assistant", "ai"):
            return getattr(m, "content", "") or ""
    return ""


def _unwrap_agent_code(txt: str) -> str:
    m = re.search(r"```(?:python)?\n([\s\S]*?)```", txt)
    if m:
        return m.group(1)
    return txt


def _generate_l3_factor_code(view: CodeGenView) -> str:
    """使用 L3 专用 ReAct agent 生成 FactorBase 规范代码。"""
    agent = _build_l3_codegen_agent()
    if agent is None:
        print("[DBG] _generate_l3_factor_code fallback without llm")
        # 简单回退：生成一个占位因子，避免空结果影响流程
        return (
            "from L3FactorFrame.FactorBase import FactorBase\n\n"
            f"class {view.factor_name}(FactorBase):\n"
            "    def __init__(self, config, factorManager, marketDataManager):\n"
            "        super().__init__(config, factorManager, marketDataManager)\n"
            "    def calculate(self):\n"
            "        self.addFactorValue(0.0)\n"
        )

    sem = view.check_semantics
    last_error = sem.last_error if sem else ""
    # If no explicit last_error but reasons exist, join them
    if sem and sem.reason and not last_error:
        last_error = "; ".join(sem.reason)

    # Inject NonFactor info into the prompt
    formatted_prompt = PROMPT_FACTOR_L3_PY.format(
        nonfactor_infos=get_formatted_nonfactor_info()
    )
    sys = SystemMessage(content=formatted_prompt)

    user_content = (
        f"因子类名: {view.factor_name}\n"
        f"因子需求描述: {view.user_spec}\n"
    )
    if last_error:
         user_content += f"\n[上一轮错误摘要]\n{last_error[:2000]}\n"

    user = HumanMessage(content=user_content)
    
    try:
        out = agent.invoke({"messages": [sys, user]})
        msgs = out.get("messages") or []
        print(
            "[DBG] _generate_l3_factor_code agent invoked",
            f"msgs={len(msgs)} last_error={(last_error[:80]+'...') if last_error else 'none'}",
        )
        txt = _extract_last_assistant_content(msgs)
        return _unwrap_agent_code(txt).strip()
    except Exception as e:
        print(f"[DBG] Agent invoke failed: {e}")
        return f"# Agent invoke failed: {e}\nclass {view.factor_name}(FactorBase):\n    pass"


def generate_factor_code_from_spec(state: FactorAgentState) -> str:
    view = CodeGenView.from_state(state)
    # Handle string or Enum comparison
    if view.code_mode == CodeMode.L3_PY or view.code_mode == "l3_py":
        return _generate_l3_factor_code(view)

    body = simple_factor_body_from_spec(view.user_spec)
    return render_factor_code(view.factor_name, view.user_spec, body)


def run_factor(state: FactorAgentState) -> Dict[str, Any]:
    view = CodeGenView.from_state(state)
    if view.code_mode == CodeMode.L3_PY or view.code_mode == "l3_py":
        res = _mock_run(view.factor_code)
        if res.get("ok"):
            # Map L3 result to stdout for display compatibility
            val_preview = str(res.get("result"))
            if len(val_preview) > 1000:
                val_preview = val_preview[:1000] + "... (truncated)"
            return {
                "success": True, 
                "result": res.get("result"),
                "stdout": f"[L3 Mock Result]\n{val_preview}"
            }
        return {
            "success": False, 
            "traceback": res.get("error"),
            "stderr": res.get("error")
        }

    return run_code(
        view.factor_code,
        entry="run_factor",
        args={"args": ["2020-01-01", "2020-01-10", ["A"]], "kwargs": {}},
    )


def is_semantic_check_ok(state: FactorAgentState) -> tuple[bool, Dict[str, Any]]:
    view = CodeGenView.from_state(state)
    
    if view.code_mode == CodeMode.L3_PY or view.code_mode == "l3_py":
        reasons = []
        code = view.factor_code
        
        if "FactorBase" not in code:
            reasons.append("未继承 FactorBase。")
        if "def calculate" not in code:
            reasons.append("未定义 calculate 方法。")
        if "addFactorValue" not in code:
            reasons.append("未调用 addFactorValue 写回因子值。")
        
        # Check inheritance from syntax check tool if needed, but simple string check is fast
        
        passed = len(reasons) == 0
        last_err = "; ".join(reasons) if reasons else ""
        
        result = SemanticCheckResult(
            passed=passed,
            reason=reasons,
            last_error=last_err
        )
        # Return as dict to match state structure
        return passed, result.model_dump()

    # pandas 模式保持兼容
    detail = view.check_semantics or SemanticCheckResult()
    # view.check_semantics might be a dict if coming from raw state, or object if processed
    if isinstance(detail, SemanticCheckResult):
        return detail.passed, detail.model_dump()
    
    ok = detail.get("passed", detail.get("pass", True))
    return ok, detail


if __name__=="__main__":
    # 生成一个l3_factor类的因子
    # 构造一个测试用的 state
    test_state = FactorAgentState(
        user_spec="请计算档期主买主卖的订单不均衡",
        factor_name="AskBidRate",
        code_mode="l3_py"
    )

    # 调用生成函数
    generated_code = generate_factor_code_from_spec(test_state)
    print("=== 生成的 L3 因子代码 ===")
    print(generated_code)

    # 可选：将生成的代码写回 state 并做语义检查
    test_state["factor_code"] = generated_code
    passed, semantic_result = is_semantic_check_ok(test_state)
    print("\n=== 语义检查结果 ===")
    print("通过:", passed)
    print("详情:", semantic_result)
