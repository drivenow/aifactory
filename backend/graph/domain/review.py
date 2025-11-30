# backend/graph/domain/review.py
from __future__ import annotations

import json
from pydantic import BaseModel, Field
from typing import Any, Dict, Tuple, Optional

from ..state import FactorAgentState, ViewBase, HumanReviewStatus

class HumanReviewView(ViewBase):
    """
    人审相关视图：构造前端需要的 payload 字段
    """
    factor_code: str = ""
    retry_count: int = 0
    ui_request: Optional[Dict[str, Any]]      # 后端发起的人审请求 payload
    ui_response: Optional[Dict[str, Any]]     # 前端回传的人审结果 payload
    human_review_status: HumanReviewStatus    # 人审状态：pending/edited/approved/rejected
    human_edits: Optional[str]                # 人工修改后的代码
    should_interrupt: bool = True   # 是否进入 HITL 中断（诊断/前端显示）

    @classmethod
    @ViewBase._wrap_from_state("HumanReviewView.from_state")
    def from_state(cls, state: FactorAgentState) -> "HumanReviewView":
        return cls(
            factor_code=state.get("factor_code") or "",
            retry_count=int(state.get("retry_count") or 0),
            ui_request=state.get("ui_request"),
            ui_response=state.get("ui_response"),
            human_review_status=state.get("human_review_status"),
            human_edits=state.get("human_edits"),
            should_interrupt=state.get("should_interrupt", False),
        )



def build_human_review_request(state: FactorAgentState) -> Dict[str, Any]:
    """
    构造人审请求 payload，交给前端渲染 CodeReviewPanel。
    """
    view = HumanReviewView.from_state(state)

    req: Dict[str, Any] = {
        "type": "code_review",
        "title": "Review generated factor code",
        "code": view.factor_code,
        "actions": str(HumanReviewStatus.__args__),
        "retry_count": view.retry_count,
    }
    return req



def normalize_review_response(raw: Any) -> Tuple[Dict[str, Any], str, str | None]:
    """
    解析并标准化前端回传的人审结果 ui_resp。

    输入可能是：
    - 字符串（"approved"/"rejected"/"edited" 或 JSON 字符串）
    - dict（包含 status / human_review_status / edited_code / factor_code 等）
    - 其他类型（做兜底）

    返回：
    - ui_resp: dict 形式的标准化对象
    - status: "approved"/"edited"/"rejected" 之一（异常时默认为 "rejected"）
    - edited_code: 如存在则返回，否则为 None
    """
    ui_resp = raw

    # 1) 字符串 → 尝试当 JSON 解析
    if isinstance(ui_resp, str):
        try:
            ui_resp = json.loads(ui_resp)
        except Exception:
            ui_resp = {"status": ui_resp}

    # 3) 把“嵌套的 status”解开
    status_raw = ui_resp.get("status") or ui_resp.get("human_review_status")
    if isinstance(status_raw, dict):
        status = status_raw.get("status") or status_raw.get("human_review_status")
    else:
        status = status_raw

    edited_code = ui_resp.get("edited_code") or ui_resp.get("factor_code")

    if not isinstance(status, str):
        status = "rejected"

    return ui_resp, status, edited_code
