# backend/graph/nodes.py
from __future__ import annotations

from typing import Dict, Any, Optional, List
from langgraph.graph import END
from langgraph.types import interrupt

from global_state import FactorAgentState, FactorAgentStateModel, HumanReviewStatus
from domain import (
    extract_spec_and_name,
    generate_factor_code_from_spec,
    run_factor,
    is_semantic_check_ok,
    compute_eval_metrics,
    write_factor_and_metrics,
    build_human_review_request,
    normalize_review_response,
)
from .config import RETRY_MAX

# -------------------------
# Retry routing helper
# -------------------------

def _route_retry_or_human_review(
    state: FactorAgentState,
    update: Dict[str, Any],
    target_if_retry: str = "generate_factor_code",
) -> Dict[str, Any]:
    """
    根据 retry_count 路由到重试节点或 HITL 节点。

    - 如果 retry_count >= RETRY_MAX，进入 HITL 节点（默认 "human_review_gate"）
    - 否则，进入重试节点（默认 "generate_factor_code"）
    """
    current = int(state.get("retry_count", 0))

    # ✅ 只要当前代码是人 edit 后的版本，失败就不自动重试，直接回 HITL
    if state.get("human_review_status") == "edit":
        rc = int(state.get("retry_count", 0)) + 1
        return {
            **update,
            "retry_count": rc,
            "route": "human_review_gate",
            "enable_interrupt": True,
            "ui_response": None,   # ⭐ 关键：下次一定会重新 interrupt
            "ui_request": None,  # 可选，顺手清掉
        }

    if current >= RETRY_MAX:
        return {
            **update,
            "retry_count": current,
            "enable_interrupt": True,
            "route": "human_review_gate",
        }

    return {
        **update,
        "retry_count": current + 1,
        "route": target_if_retry,
    }


# -------------------------
# Nodes
# -------------------------

def collect_spec_from_messages(state: FactorAgentState) -> Dict[str, Any]:
    """
    收集用户因子描述与名称，并进入代码生成阶段。
    state: 实际传递的是一个dict
    - 从 state.user_spec 或 messages[-1] 中提取描述
    """
    spec, name = extract_spec_and_name(state)

    print(
        f"[DBG] collect_spec_from_messages thread={state.get('thread_id')} "
        f"spec_len={len(spec) if isinstance(spec, str) else 0} name={name}"
    )

    return {
        "user_spec": spec,
        "factor_name": name,
        "retry_count": int(state.get("retry_count", 0)),
        "code_mode": state.get("code_mode") or "pandas",
        "last_success_node": "collect_spec_from_messages",
        "state_error": None,
        "route": "generate_factor_code",
    }


def generate_factor_code(state: FactorAgentState) -> Dict[str, Any]:
    try:
        code = generate_factor_code_from_spec(state)

        print(
            f"[DBG] generate_factor_code thread={state.get('thread_id')} "
            f"code_len={len(code) if isinstance(code, str) else 0}"
        )

        return {
            "factor_code": code,
            "last_success_node": "generate_factor_code",
            "state_error": None,
            "route": "run_factor_dryrun",
        }

    except Exception as e:
        print(
            f"[DBG] generate_factor_code error thread={state.get('thread_id')} msg={str(e)}"
        )
        return _route_retry_or_human_review(
            state,
            {
                "state_error": ["generate_factor_code error: "+ str(e)],
                "last_success_node": "generate_factor_code",
            },
            target_if_retry="generate_factor_code",
        )


def run_factor_dryrun(state: FactorAgentState) -> Dict[str, Any]:
    result = run_factor(state)
    success = bool(result.get("success"))
    trace = result.get("result")

    print(
        f"[DBG] run_factor_dryrun thread={state.get('thread_id')} , "
        f"success={success}, result={trace}, retry_count={state.get('retry_count', 0)}"
    )

    if success:
        return {
            "dryrun_result": {"success": True, "stdout": trace},
            "check_semantics": {"last_error": None},
            "last_success_node": "run_factor_dryrun",
            "state_error": None,
            "route": "check_semantics",
        }

    return _route_retry_or_human_review(
        state,
        {
            "dryrun_result": {
                "success": False,
                "result": result.get("result"),
            },
            "check_semantics": {
                "pass": False,
                "last_error": trace,
            },
            "state_error": ["run_factor_dryrun failed"],
            "last_success_node": "run_factor_dryrun",
        },
        target_if_retry="generate_factor_code",
    )


def check_semantics(state: FactorAgentState) -> Dict[str, Any]:
    check_result, check_detail = is_semantic_check_ok(state)

    print(f"[DBG] check_semantics thread={state.get('thread_id')} ok={check_result} detail={check_detail}")

    if check_result:    
        return {
            "check_semantics": check_detail or {"pass": True},
            "last_success_node": "check_semantics",
            "state_error": None,
            "route": "human_review_gate",
        }

    update = {
        "check_semantics": check_detail
        or {
            "pass": False,
            "reason": "spec/code/run_factor_dryrun mismatch",
        },
        "state_error": ["check_semantics failed"],
        "last_success_node": "check_semantics",
    }
    update2 = _route_retry_or_human_review(state, update, target_if_retry="generate_factor_code")
    print("[DBG] check_semantics fail update=", update2)
    return update2


def human_review_gate(state: FactorAgentState) -> Dict[str, Any]:
    """
    人工审核节点（HITL）
    - 发起 interrupt，把 req 传出去
    - 恢复后统一解析前端回传payload(带thread_id), 后端进行处理：
      新协议 action+payload 优先，
    """
    # 默认需要中断
    enable_interrupt = state.get("enable_interrupt", True)
    if not enable_interrupt:
        final_code = state.get("factor_code") or ""
        return {
            "human_review_status": "approve",
            "factor_code": final_code,
            "route": "backfill_and_eval",
            "last_success_node": "human_review_gate",
            "retry_count": 0,
            "ui_request": state.get("ui_request"),
            "ui_response": state.get("ui_response"),
        }

    req = {
        "type": "code_review",
        "title": "Review generated factor code",
        "code": state.get("factor_code", "") or "",
        "actions": str(HumanReviewStatus.__args__),
        "retry_count": int(state.get("retry_count", 0)),
    }
    ui_resp_raw = interrupt(req)
    # 允许前端传 string/json/dict 等多形态
    ui_resp, status, edited_code = normalize_review_response(ui_resp_raw)

    # =====（推荐 action+payload）=====
    action = None
    payload = {}

    # 1) 新协议优先：{action, payload}
    if isinstance(ui_resp, dict) and ui_resp.get("action"):
        action = ui_resp.get("action")
        payload = ui_resp.get("payload") or {}

    action_norm = action or status or "reject"
    review_comment = payload.get("review_comment") if isinstance(payload, dict) else None
    edited_code = payload.get("edited_code") if isinstance(payload, dict) else edited_code

    # ---- approve / edit 通过 ----
    if action_norm in ("approve", "edit"):
        final_code = edited_code or state.get("factor_code")
        print(f"[DBG] human_review_gate approve/edit final_code={final_code}, retry_count reset to 0.")
        # 公共 update 字段
        base_update = {
            "ui_request": req,
            "ui_response": ui_resp,
            "human_review_status": "edit" if action_norm == "edit" else "approve",
            "human_edits": edited_code,
            "factor_code": final_code,
            "review_comment": review_comment,
            "last_success_node": "human_review_gate",
            "state_error": None,
            "retry_count": 0, # 人工审核通过后，重置 retry_count
        }

        # ✅ 情况 1：用户只是 approve，不改代码 → 可以直通 backfill
        if action_norm == "approve":
            return {
                **base_update,
                "route": "backfill_and_eval",
            }

        # ✅ 情况 2：用户 edit 了代码 → 回到 run_factor_dryrun 重新跑一遍
        if action_norm == "edit":
            return {
                **base_update,
                "route": "run_factor_dryrun",
                # 可选：把旧的 run_factor_dryrun/check_semantics 结果清空或标记为过期
                "dryrun_result": {},
                "semantic_ok": False,
            }

    # ---- review 只给意见 → 回到 generate_factor_code ----
    elif action_norm == "review":
        comment = (review_comment or "").strip()
        new_spec = (state.get("user_spec") or "") + f"\n\n[REVIEW COMMENT]\n{comment}"
        return {
            "user_spec": new_spec,
            "human_review_status": "review",
            "review_comment": comment,
            "last_success_node": "human_review_gate",
            "state_error": None,
            "route": "generate_factor_code",
        }

    # ---- reject 结束 ----
    elif action_norm == "reject":
        return {
            "ui_request": req,
            "ui_response": ui_resp,
            "human_review_status": "reject",
            "review_comment": review_comment,
            "last_success_node": "human_review_gate",
            "state_error": None,
            "route": "finish",
        }
    else:
        print(f"[DBG] human_review_gate invalid action={action_norm!r}")
        # ---- 兜底非法 action ----
        return {
            "ui_request": req,
            "ui_response": ui_resp,
            "human_review_status": "reject",
            "review_comment": review_comment,
            "last_success_node": "human_review_gate",
            "state_error": [f"human_review_gate invalid ui_response action={action!r}"],
            "route": "finish",
        }



def backfill_and_eval(state: FactorAgentState) -> Dict[str, Any] :
    # 这里可以选择性全量校验一次（高价值节点）
    FactorAgentStateModel.from_state(state)

    metrics = compute_eval_metrics(state)
    print(
        f"[DBG] backfill_and_eval thread={state.get('thread_id')} "
        f"metrics_keys={list(metrics.keys())}"
    )

    return {
        "eval_metrics": metrics,
        "last_success_node": "backfill_and_eval",
        "state_error": None,
        "route": "write_db",
    }


def write_db(state: FactorAgentState) -> Dict[str, Any] :
    res = write_factor_and_metrics(state)

    print(
        f"[DBG] write_db thread={state.get('thread_id')} "
        f"status={res.get('status', 'unknown')}"
    )

    return {
        "db_write_status": res.get("status", "success"),
        "last_success_node": "write_db",
        "state_error": None,
        "route": "finish",
    }


def finish(state: FactorAgentState) -> Dict[str, Any]:
    print(f"[DBG] finish thread={state.get('thread_id')}")
    return {}


"""
工作流节点实现（纯 route+conditional edges 控制）

节点：
- collect_spec_from_messages: 收集用户描述
- generate_factor_code: 按模板生成代码
- run_factor_dryrun: 沙盒运行
- check_semantics: 语义检查
- human_review_gate: AG-UI HITL（ui_request/ui_response）
- backfill_and_eval: mock 回填评价
- write_db: mock 入库
- finish: 结束

重试：
- retry_count 在 _route_retry_or_human_review 中单点管理
- retry_count >= RETRY_MAX 强制进入 human_review_gate
"""
