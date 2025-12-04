from __future__ import annotations

from typing import Any, List, Optional
import re

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage

from backend.graph.config import get_llm
from backend.graph.prompts.factor_l3_py import PROMPT_FACTOR_L3_PY
from backend.graph.tools.codebase_fs_tools import read_repo_file, list_repo_dir
from .tools.l3_factor_tool import l3_syntax_check, l3_mock_run
from .tools.nonfactor_info import get_formatted_nonfactor_info
from .view import CodeGenView

_L3_AGENT: Optional[Any] = None


def create_agent(llm: Any, tools: Optional[List[Any]] = None):
    """Thin wrapper to allow monkeypatch in tests."""
    return create_react_agent(llm, tools=tools)


def build_l3_codegen_agent():
    """Build or reuse cached L3 ReAct agent."""
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

    _L3_AGENT = create_agent(llm, tools=tools)
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


def build_l3_user_message(view: CodeGenView) -> HumanMessage:
    sem = view.check_semantics
    last_error = sem.last_error if sem else ""
    if sem and sem.reason and not last_error:
        last_error = "; ".join(sem.reason)

    user_content = (
        f"因子类名: {view.factor_name}\n"
        f"因子需求描述: {view.user_spec}\n"
    )
    if last_error:
        user_content += f"\n[上一轮错误摘要]\n{last_error[:2000]}\n"

    return HumanMessage(content=user_content)


def invoke_l3_agent(view: CodeGenView) -> str:
    """使用 L3 专用 ReAct agent 生成 FactorBase 规范代码。"""
    agent = build_l3_codegen_agent()
    if agent is None:
        # 简单回退：生成一个占位因子，避免空结果影响流程
        return (
            "from L3FactorFrame.FactorBase import FactorBase\n\n"
            f"class {view.factor_name}(FactorBase):\n"
            "    def __init__(self, config, factorManager, marketDataManager):\n"
            "        super().__init__(config, factorManager, marketDataManager)\n"
            "    def calculate(self):\n"
            "        self.addFactorValue(0.0)\n"
        )

    formatted_prompt = PROMPT_FACTOR_L3_PY.format(
        nonfactor_infos=get_formatted_nonfactor_info()
    )
    sys = SystemMessage(content=formatted_prompt)
    user = build_l3_user_message(view)

    try:
        out = agent.invoke({"messages": [sys, user]})
        msgs = out.get("messages") or []
        txt = _extract_last_assistant_content(msgs)
        return _unwrap_agent_code(txt).strip()
    except Exception as e:
        return f"# Agent invoke failed: {e}\nclass {view.factor_name}(FactorBase):\n    pass"
