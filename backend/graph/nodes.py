# backend/graph/nodes.py
from __future__ import annotations

from typing import Dict, Any, Optional, List
from langgraph.graph import END
from langgraph.types import Command, interrupt

from .state import FactorAgentState, FactorAgentStateModel, HumanReviewStatus
from .domain.logic import extract_spec_and_name
from .domain.codegen import (
    generate_factor_code_from_spec,
    run_factor_dryrun,
    is_semantic_check_ok,
)
from .domain.eval import compute_eval_metrics, write_factor_and_metrics
from .domain.review import build_human_review_request, normalize_review_response
from .config import RETRY_MAX

# -------------------------
# Retry routing helper
# -------------------------

def _route_retry_or_hitl(
    state: FactorAgentState,
    update: Dict[str, Any],
    target_if_retry: str = "gen_code_react",
) -> Dict[str, Any]:
    """
    根据 retry_count 路由到重试节点或 HITL 节点。

    - 如果 retry_count >= RETRY_MAX，进入 HITL 节点（默认 "human_review_gate"）
    - 否则，进入重试节点（默认 "gen_code_react"）
    """
    current = int(state.get("retry_count", 0))

    if current >= RETRY_MAX:
        return {
            **update,
            "retry_count": current,
            "should_interrupt": True,
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
        "last_success_node": "collect_spec_from_messages",
        "error": None,
        "route": "gen_code_react",
    }


def gen_code_react(state: FactorAgentState) -> Dict[str, Any]:
    try:
        code = generate_factor_code_from_spec(state)

        print(
            f"[DBG] gen_code_react thread={state.get('thread_id')} "
            f"code_len={len(code) if isinstance(code, str) else 0}"
        )

        return {
            "factor_code": code,
            "last_success_node": "gen_code_react",
            "error": None,
            "route": "dryrun",
        }

    except Exception as e:
        print(
            f"[DBG] gen_code_react error thread={state.get('thread_id')} msg={str(e)}"
        )
        return _route_retry_or_hitl(
            state,
            {
                "error": {"node": "gen_code_react", "message": str(e)},
                "last_success_node": "gen_code_react",
            },
            target_if_retry="gen_code_react",
        )


def dryrun(state: FactorAgentState) -> Dict[str, Any]:
    result = run_factor_dryrun(state)
    success = bool(result.get("success"))

    print(
        f"[DBG] dryrun thread={state.get('thread_id')} "
        f"success={success} retry_count={state.get('retry_count', 0)}"
    )

    if success:
        return {
            "dryrun_result": {"success": True, "stdout": result.get("stdout", "")},
            "last_success_node": "dryrun",
            "error": None,
            "route": "semantic_check",
        }

    return _route_retry_or_hitl(
        state,
        {
            "dryrun_result": {
                "success": False,
                "traceback": result.get("traceback"),
                "stderr": result.get("stderr", ""),
            },
            "error": {"node": "dryrun", "message": "dryrun failed"},
            "last_success_node": "dryrun",
        },
        target_if_retry="gen_code_react",
    )


def semantic_check(state: FactorAgentState) -> Dict[str, Any]:
    check_result, check_detail = is_semantic_check_ok(state)

    print(f"[DBG] semantic_check thread={state.get('thread_id')} ok={check_result} detail={check_detail}")

    if check_result:    
        return {
            "semantic_check": {"pass": True},
            "last_success_node": "semantic_check",
            "error": None,
            "route": "human_review_gate",
        }

    update = {
        "semantic_check": {
            "pass": False,
            "reason": "spec/code/dryrun mismatch",
        },
        "error": {
            "node": "semantic_check",
            "message": "semantic_check failed",
        },
        "last_success_node": "semantic_check",
    }
    update2 = _route_retry_or_hitl(state, update, target_if_retry="gen_code_react")
    print("[DBG] semantic_check fail update=", update2)
    return update2


def human_review_gate(state: FactorAgentState) -> Command:
    """
    人工审核节点（HITL）
    - 发起 interrupt，把 req 传出去
    - 恢复后统一解析前端回传：
      新协议 action+payload 优先，旧协议 status 兜底
    """
    req = {
        "type": "code_review",
        "title": "Review generated factor code",
        "code": state.get("factor_code", "") or "",
        "actions": str(HumanReviewStatus.__args__),
        "retry_count": int(state.get("retry_count", 0)),
    }

    # 第一次进入：中断并把 req 发给前端
    ui_resp_raw = interrupt(req)

    # 允许前端传 string/json/dict 等多形态
    ui_resp, status, edited_code = normalize_review_response(ui_resp_raw)

    # ===== 新旧协议统一层（推荐 action+payload）=====
    action = None
    payload = {}

    # 1) 新协议优先：{action, payload}
    if isinstance(ui_resp, dict) and ui_resp.get("action"):
        action = ui_resp.get("action")
        payload = ui_resp.get("payload") or {}

    # 2) 旧协议兜底：{status, review_comment, edited_code}
    if action is None:
        print(f"[DBG] human_review_gate old protocol status={status}")

    action_norm = action or "reject"
    review_comment = payload.get("review_comment") if isinstance(payload, dict) else None
    edited_code = payload.get("edited_code") if isinstance(payload, dict) else edited_code

    # ---- approve / edit 通过 ----
    if action_norm in ("approve", "edit"):
        final_code = edited_code or state.get("factor_code")

        # 公共 update 字段
        base_update = {
            "ui_request": req,
            "ui_response": ui_resp,
            "human_review_status": "edited" if action_norm == "edited" else "approved",
            "human_edits": edited_code,
            "factor_code": final_code,
            "review_comment": review_comment,
            "last_success_node": "human_review_gate",
            "error": None,
        }

        # ✅ 情况 1：用户只是 approve，不改代码 → 可以直通 backfill
        if action_norm == "approve":
            return Command(
                goto="backfill_and_eval",
                update={
                    **base_update,
                    "route": "backfill_and_eval",
                },
            )

        # ✅ 情况 2：用户 edit 了代码 → 回到 dryrun 重新跑一遍
        if action_norm == "edit":
            return Command(
                goto="dryrun",
                update={
                    **base_update,
                    "route": "dryrun",
                    # 可选：把旧的 dryrun/semantic_check 结果清空或标记为过期
                    "dryrun_result": {},
                    "semantic_ok": False,
                },
            )

    # ---- review 只给意见 → 回到 gen_code_react ----
    elif action_norm == "review":
        comment = (review_comment or "").strip()
        new_spec = (state.get("user_spec") or "") + f"\n\n[REVIEW COMMENT]\n{comment}"
        return Command(
            goto="gen_code_react",
            update={
                "user_spec": new_spec,
                "human_review_status": "review",
                "review_comment": comment,
                "last_success_node": "human_review_gate",
                "error": None,
                "route": "gen_code_react",
            },
        )

    # ---- reject 结束 ----
    elif action_norm == "rejecte":
        return Command(
            goto="finish",
            update={
                "ui_request": req,
                "ui_response": ui_resp,
                "human_review_status": "rejecte",
                "review_comment": review_comment,
                "last_success_node": "human_review_gate",
                "error": None,
                "route": "finish",
            },
        )
    else:
        print(f"[DBG] human_review_gate invalid action={action_norm!r}")
        # ---- 兜底非法 action ----
        return Command(
            goto="finish",
            update={
                "ui_request": req,
                "ui_response": ui_resp,
                "human_review_status": "rejecte",
                "review_comment": review_comment,
                "last_success_node": "human_review_gate",
                "error": {
                    "node": "human_review_gate",
                    "message": f"invalid ui_response action={action!r}",
                },
                "route": "finish",
            },
    )



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
        "error": None,
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
        "error": None,
        "route": "finish",
    }


def finish(state: FactorAgentState) -> Dict[str, Any] | Command:
    print(f"[DBG] finish thread={state.get('thread_id')}")
    return {}


"""
工作流节点实现（纯 Command 路由，方案 A）

节点：
- collect_spec_from_messages: 收集用户描述
- gen_code_react: 按模板生成代码
- dryrun: 沙盒运行
- semantic_check: 语义检查
- human_review_gate: AG-UI HITL（ui_request/ui_response）
- backfill_and_eval: mock 回填评价
- write_db: mock 入库
- finish: 结束

重试：
- retry_count 在 _route_retry_or_hitl 中单点管理
- retry_count >= RETRY_MAX 强制进入 human_review_gate
"""
