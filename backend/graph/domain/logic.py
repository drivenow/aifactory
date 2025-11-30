# backend/graph/domain/logic.py
from __future__ import annotations

from typing import Tuple, Any, Dict, List

from ..state import FactorAgentState


def extract_spec_and_name(state: FactorAgentState) -> Tuple[str, str]:
    """
    从当前状态中提取用户因子描述和名称。

    优先级：
    1. state.user_spec
    2. state.messages[-1].content / .text / 直接 str(last)
    3. 默认为空字符串
    """
    spec = state.get("user_spec")
    messages: List[Dict[str, Any]] = state.get("messages", []) or []

    if not spec:
        spec = ""
        if isinstance(messages, list) and messages:
            last = messages[-1]
            if isinstance(last, dict):
                spec = last.get("content", "") or str(last)
            else:
                # LangGraph / CopilotKit 消息对象的容错提取
                c = getattr(last, "content", None)
                if c is None:
                    c = getattr(last, "text", None)
                spec = c if c is not None else str(last)

    name = state.get("factor_name") or "factor"
    return spec, name
