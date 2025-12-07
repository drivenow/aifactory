from __future__ import annotations

from typing import Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from domain.llm import create_agent, _extract_last_assistant_content, _unwrap_agent_code
from domain.codegen.prompts.factor_l3_py import PROMPT_FACTOR_L3_PY
from domain.codegen.prompts.factor_l3_cpp import PROMPT_FACTOR_L3_CPP
from domain.codegen.prompts.semantic_check import SEMANTIC_CHECK_PROMPT
# from .tools.codebase_fs_tools import read_repo_file, list_repo_dir
from domain.codegen.tools import (
    l3_syntax_check, 
    l3_mock_run,
    get_formatted_nonfactor_info_py,
    get_formatted_nonfactor_info_cpp,
)
from domain.codegen.view import CodeGenView, DryrunResult, SemanticCheckResult


_L3_AGENT: Optional[Any] = None
_L3_CPP_AGENT: Optional[Any] = None
_SEMANTIC_AGENT: Optional[Any] = None


def build_l3_codegen_agent():
    """Build or reuse cached L3 ReAct agent."""
    global _L3_AGENT
    if _L3_AGENT is not None:
        return _L3_AGENT

    tools = [
        l3_syntax_check,
        l3_mock_run,
    ]

    _L3_AGENT = create_agent(tools=tools)
    return _L3_AGENT


def build_l3_user_message(view: CodeGenView) -> HumanMessage:
    sem = view.check_semantics
    last_error = sem.last_error if sem else ""
    if sem and sem.reason and not last_error:
        last_error = "; ".join(sem.reason)

    user_content = (
        f"因子类名: {view.factor_name}\n"
        f"因子需求描述: {view.user_spec}\n"
        f"因子代码: {view.factor_code}\n" if view.factor_code else ""
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

    formatted_prompt = PROMPT_FACTOR_L3_PY.replace(
        "{nonfactor_infos}", get_formatted_nonfactor_info_py()
    )
    sys = SystemMessage(content=formatted_prompt)
    user = build_l3_user_message(view)

    try:
        out = agent.invoke({"messages": [sys, user]})
        msgs = out.get("messages") or []
        txt = _extract_last_assistant_content(msgs)
        return _unwrap_agent_code(txt).strip()
    except Exception as e:
        return f"ERROR: Agent invoke failed: {e}\nclass {view.factor_name}(FactorBase):\n    pass"


def build_l3_cpp_codegen_agent():
    """Build or reuse cached L3 C++ ReAct agent."""
    global _L3_CPP_AGENT
    if _L3_CPP_AGENT is not None:
        return _L3_CPP_AGENT

    tools: List[Any] = []
    _L3_CPP_AGENT = create_agent(tools=tools)
    return _L3_CPP_AGENT


def invoke_l3_cpp_agent(view: CodeGenView) -> str:
    """使用 L3 C++ 专用 ReAct agent 生成 Factor SDK 规范代码。"""
    agent = build_l3_cpp_codegen_agent()
    if agent is None:
        return (
            "// Agent 未配置，返回占位实现\n"
            "#include <stdexcept>\n"
            f"struct {view.factor_name}Param {{}};\n"
            f"class {view.factor_name} {{}};\n"
        )

    formatted_prompt = PROMPT_FACTOR_L3_CPP.replace(
        "{nonfactor_infos}", get_formatted_nonfactor_info_cpp()
    )
    sys = SystemMessage(content=formatted_prompt)
    user = build_l3_user_message(view)

    try:
        out = agent.invoke({"messages": [sys, user]})
        msgs = out.get("messages") or []
        txt = _extract_last_assistant_content(msgs)
        return _unwrap_agent_code(txt, lang="cpp").strip()
    except Exception as e:
        return f"// ERROR: Agent invoke failed: {e}\n"


def build_semantic_agent():
    """LLM agent for semantic validation (no external tools)."""
    global _SEMANTIC_AGENT
    if _SEMANTIC_AGENT is not None:
        return _SEMANTIC_AGENT
    _SEMANTIC_AGENT = create_agent(tools=[])
    return _SEMANTIC_AGENT


def invoke_semantic_agent(view: CodeGenView, dryrun: DryrunResult) -> SemanticCheckResult:
    """调用语义审核 agent，返回标准化结果。"""
    agent = build_semantic_agent()
    if agent is None:
        # fallback handled in caller
        return SemanticCheckResult(passed=False, reason=["semantic agent unavailable"], last_error="semantic agent unavailable")

    user_content = (
        f"因子名称: {view.factor_name}\n"
        f"用户需求: {view.user_spec}\n"
        "因子代码:\n"
        f"```python\n{view.factor_code}\n```\n"
        "运行输出:\n"
        f"stdout:\n{dryrun.stdout or ''}\n"
        f"stderr:\n{dryrun.stderr or ''}\n"
    )
    sys = SystemMessage(content=SEMANTIC_CHECK_PROMPT)
    user = HumanMessage(content=user_content)

    try:
        out = agent.invoke({"messages": [sys, user]})
        msgs = out.get("messages") or []
        txt = _extract_last_assistant_content(msgs)
        return _parse_semantic_json(txt)
    except Exception as e:
        return SemanticCheckResult(passed=False, reason=[f"semantic agent error: {e}"], last_error=str(e))


def _parse_semantic_json(txt: str) -> SemanticCheckResult:
    import json, re
    text = txt or ""
    try:
        obj = json.loads(text)
        return _semantic_from_mapping(obj)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            obj = json.loads(m.group(0))
            return _semantic_from_mapping(obj)
        except Exception:
            pass
    lowered = text.lower()
    passed = "true" in lowered and "false" not in lowered
    reason = [text.strip()] if text.strip() else []
    return SemanticCheckResult(passed=passed, reason=reason, last_error="; ".join(reason) if reason else None)


def _semantic_from_mapping(obj):
    passed = bool(obj.get("passed"))
    reason = obj.get("reason") or obj.get("reasons") or []
    if isinstance(reason, str):
        reason = [reason]
    return SemanticCheckResult(passed=passed, reason=reason, last_error="; ".join(reason) if reason else None)
