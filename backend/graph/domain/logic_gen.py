# backend/graph/domain/logic.py
from __future__ import annotations

from typing import Tuple, Any, Dict, List
from pydantic import BaseModel, Field
from typing import Tuple, Any, Dict, List
from global_state import FactorAgentState, ViewBase

class LogicView(ViewBase):
    """
    Logic 领域视图：只关心自己用到的字段

    - messages: 用于兜底提取 user_spec
    - user_spec: 用户因子描述，默认空串
    - factor_name: 因子名，默认 "factor"
    """
    messages: List[Any] = Field(default_factory=list)
    user_spec: str = ""
    factor_name: str = "factor"

    @classmethod
    @ViewBase._wrap_from_state("LogicView.from_state")
    def from_state(cls, state: FactorAgentState) -> "LogicView":
        return cls(
            messages=state.get("messages") or [],
            user_spec=state.get("user_spec") or "",
            factor_name=state.get("factor_name") or "factor",
        )



def extract_spec_and_name(state: FactorAgentState) -> Tuple[str, str]:
    """
    从当前状态中提取用户因子描述和名称。

    优先级：
    1. state.user_spec
    2. state.messages[-1].content / .text / 直接 str(last)
    3. 默认为空字符串
    """
    view = LogicView.from_state(state)

    spec = view.user_spec
    messages = view.messages

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

    name = view.factor_name or "factor"
    return spec, name
