# backend/graph/domain/review.py
from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from ..state import FactorAgentState


def build_human_review_request(state: FactorAgentState) -> Dict[str, Any]:
    """
    构造人审请求 payload，交给前端渲染 CodeReviewPanel。

    前端目前依赖字段：
    - type: "code_review"
    - title: 标题
    - code: 当前因子代码
    - actions: ["approve", "edit", "reject"]
    - retry_count: 当前已重试次数
    """
    req: Dict[str, Any] = {
        "type": "code_review",
        "title": "Review generated factor code",
        "code": state.get("factor_code", "") or "",
        "actions": ["approve", "edit", "reject"],
        "retry_count": int(state.get("retry_count", 0)),
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
