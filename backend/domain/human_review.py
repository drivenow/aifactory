# backend/domain/human_review.py
from __future__ import annotations

import json
from pydantic import BaseModel, Field
from typing import Any, Dict, Tuple, Optional

from global_state import FactorAgentState, ViewBase, HumanReviewStatus

class HumanReviewView(ViewBase):
    """
    人审相关视图：构造前端需要的 payload 字段
    """
    factor_code: str = ""
    retry_count: int = 0
    ui_request: Optional[Dict[str, Any]]      # 后端发起的人审请求 payload
    ui_response: Optional[Dict[str, Any]]     # 前端回传的人审结果 payload
    human_review_status: Optional[HumanReviewStatus]    # 人审状态：pending/edit/approve/reject
    human_edits: Optional[str]                # 人工修改后的代码
    enable_interrupt: bool = True   # 是否进入 HITL 中断（诊断/前端显示）

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
            enable_interrupt=state.get("enable_interrupt", True),
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



def normalize_review_response(raw: Any) -> Tuple[Dict[str, Any], str, Optional[str]]:
    """
    解析并标准化前端回传的人审结果 ui_resp。

    2) 新推荐协议（最佳实践）：
       - dict: {action: "...", payload: {...}}
         action ∈ {"approve","reject","review","edit"}
         payload 可包含 review_comment / edited_code

    返回（保持原签名不变）：
    - ui_resp: dict 形式的标准化对象
    - status: "approve"/"edit"/"reject"/"review" 之一（异常时默认为 "reject"）
    - edited_code: 如存在则返回，否则为 None
    """
    ui_resp = raw

    # 1) 字符串 → 尝试当 JSON 解析
    if isinstance(ui_resp, str):
        try:
            ui_resp = json.loads(ui_resp)
        except Exception:
            ui_resp = {"status": ui_resp}

    if not isinstance(ui_resp, dict):
        ui_resp = {"status": "reject"}

    # 2) 新协议优先：action/payload
    if ui_resp.get("action"):
        action = ui_resp.get("action")
        payload = ui_resp.get("payload") or {}

        # action 归一化成 status
        action_map = {
            "approve": "approve",
            "reject": "reject",
            "review": "review",
            "edit": "edit",
        }
        status = action_map.get(action, "reject")

        if isinstance(payload, dict):
            edited_code = payload.get("edited_code")
        else:
            edited_code = None

        return ui_resp, status, edited_code

    edited_code = ui_resp.get("edited_code") or ui_resp.get("factor_code")
    status = ui_resp.get("status")

    if not isinstance(status, str):
        status = "reject"

    # review 也是合法状态（新加）
    if status not in ("approve", "edit", "reject", "review"):
        status = "reject"

    return ui_resp, status, edited_code
