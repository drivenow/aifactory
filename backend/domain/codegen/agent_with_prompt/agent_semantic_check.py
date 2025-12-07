from __future__ import annotations

from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from domain.codegen.view import CodeGenView, DryrunResult, SemanticCheckResult
from domain.llm import _extract_last_assistant_content, create_agent


SEMANTIC_CHECK_PROMPT = """
你是一名严格的量化因子代码审核员，请根据“用户需求、代码、运行输出”判断语义是否符合，并给出简短原因。

检查重点：
1) 代码是否满足用户需求。
2) 运行输出（stdout/stderr）是否合理，是否暴露错误。
3) 如果不符合，指出1~3条简洁原因。

响应要求：
- 仅输出 JSON，格式：{"passed": true/false, "reason": ["..."]}.
- 不要输出其他内容, 用中文来回答。
""".strip()

_SEMANTIC_AGENT: Optional[Any] = None


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
