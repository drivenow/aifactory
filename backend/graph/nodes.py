# backend/graph/nodes.py
from __future__ import annotations

from typing import Dict, Any, Optional

from pydantic import BaseModel, Field
from langgraph.graph import END
from langgraph.types import Command, interrupt

from .state import FactorAgentState
from .domain.logic import extract_spec_and_name
from .domain.codegen import (
    generate_factor_code_from_spec,
    run_factor_dryrun,
    is_semantic_check_ok,
)
from .domain.eval import compute_eval_metrics, write_factor_and_metrics
from .domain.review import build_human_review_request, normalize_review_response

RETRY_MAX = 5  # 超过该次数强制进入 HITL


# -------------------------
# Pydantic action schemas（作为结构文档/调试用）
# -------------------------

class IntentAction(BaseModel):
    """意图抽取动作输出：因子名与约束"""
    human_input: bool = False
    message: Optional[str] = None
    factor_name: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)


class CodeGenAction(BaseModel):
    """代码生成动作输出：模板化因子代码与反思备注"""
    human_input: bool = False
    message: Optional[str] = None
    factor_code: Optional[str] = None
    reflect_notes: Optional[str] = None


class DryRunResult(BaseModel):
    """试运行结果：标准化执行输出"""
    ok: bool
    stdout: str = ""
    stderr: str = ""
    traceback: str = ""


class SemanticCheckResult(BaseModel):
    """语义一致性检查：是否符合用户描述/约束"""
    ok: bool
    diffs: list[str] = Field(default_factory=list)
    reason: Optional[str] = None


class HumanReviewAction(BaseModel):
    """人审结果：审批/编辑/驳回"""
    status: str  # approved/edited/rejected
    edited_code: Optional[str] = None


class BackfillAction(BaseModel):
    """历史回填动作输出：预览统计与任务 ID"""
    ok: bool
    job_id: Optional[str] = None
    preview_stats: Dict[str, Any] = Field(default_factory=dict)


class EvalAction(BaseModel):
    """评价动作输出：各项评价指标"""
    ok: bool
    metrics: Dict[str, Any] = Field(default_factory=dict)


class PersistAction(BaseModel):
    """入库动作输出：目标地址与写入行数"""
    ok: bool
    uri: Optional[str] = None
    rows_written: int = 0


# -------------------------
# Retry routing helper
# -------------------------

def _route_retry_or_hitl(
    state: FactorAgentState,
    update: Dict[str, Any],
    target_if_retry: str = "gen_code_react",
) -> Command:
    """
    统一的重试/HITL 路由策略

    - retry_count +1
    - retry_count >= RETRY_MAX 时强制进入 HITL（goto human_review_gate）
    - 否则跳转 target_if_retry
    """
    rc = int(state.get("retry_count", 0)) + 1

    base_update = {
        **update,
        "retry_count": rc,
    }

    if rc >= RETRY_MAX:
        # 强制进入 HITL
        return Command(
            goto="human_review_gate",
            update={
                **base_update,
                "should_interrupt": True,
                "route": "human_review_gate",
            },
        )

    return Command(
        goto=target_if_retry,
        update={**base_update, "route": target_if_retry},
    )


# -------------------------
# Nodes
# -------------------------

def collect_spec(state: FactorAgentState) -> Dict[str, Any] | Command:
    """
    收集用户因子描述与名称，并进入代码生成阶段。

    - 从 state.user_spec 或 messages[-1] 中提取描述
    - 因子名默认为 "factor"
    """
    spec, name = extract_spec_and_name(state)

    print(
        f"[DBG] collect_spec thread={state.get('thread_id')} "
        f"spec_len={len(spec) if isinstance(spec, str) else 0} name={name}"
    )

    return {
        "user_spec": spec,
        "factor_name": name,
        "retry_count": int(state.get("retry_count", 0)),
        "last_success_node": "collect_spec",
        "error": None,
        "route": "gen_code_react",
    }


def gen_code_react(state: FactorAgentState) -> Dict[str, Any] | Command:
    """
    按模板生成因子代码（可以在这里替换为 ReAct 代理等更复杂的实现）

    - 使用 domain.codegen.generate_factor_code_from_spec
    - 失败时走统一重试/HITL 策略
    """
    try:
        spec = state.get("user_spec") or ""
        if not spec:
            raise ValueError("missing user_spec in state")

        name = state.get("factor_name") or "factor"
        code = generate_factor_code_from_spec(name, spec)

        print(
            f"[DBG] gen_code_react thread={state.get('thread_id')} "
            f"code_len={len(code) if isinstance(code, str) else 0}"
        )

        action = CodeGenAction(factor_code=code)

        return {
            "factor_code": action.factor_code,
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


def dryrun(state: FactorAgentState) -> Dict[str, Any] | Command:
    """
    沙盒试运行 `run_factor` 入口，成功则进入语义检查，失败则走重试/HITL。
    """
    code = state.get("factor_code", "") or ""

    result = run_factor_dryrun(code)
    success = bool(result.get("success"))

    print(
        f"[DBG] dryrun thread={state.get('thread_id')} "
        f"success={success} retry_count={state.get('retry_count')}"
    )

    if success:
        return {
            "dryrun_result": {
                "success": True,
                "stdout": result.get("stdout", ""),
            },
            "last_success_node": "dryrun",
            "error": None,
            "route": "semantic_check",
        }

    # 失败：写入错误信息 & 统一路由
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


def semantic_check(state: FactorAgentState) -> Dict[str, Any] | Command:
    """
    语义一致性检查：要求 spec、code 存在且 dryrun 成功。
    """
    spec = state.get("user_spec", "") or ""
    code = state.get("factor_code", "") or ""
    dry_ok = bool(state.get("dryrun_result", {}).get("success"))

    ok = is_semantic_check_ok(spec, code, dry_ok)
    result = SemanticCheckResult(ok=ok)

    print(f"[DBG] semantic_check thread={state.get('thread_id')} ok={result.ok}")

    if result.ok:
        return {
            "semantic_check": {"pass": True},
            "last_success_node": "semantic_check",
            "error": None,
            "route": "human_review_gate",
        }

    return _route_retry_or_hitl(
        state,
        {
            "semantic_check": {
                "pass": False,
                "reason": "spec/code/dryrun mismatch",
            },
            "error": {
                "node": "semantic_check",
                "message": "semantic_check failed",
            },
            "last_success_node": "semantic_check",
        },
        target_if_retry="gen_code_react",
    )


def human_review_gate(state: FactorAgentState) -> Command:
    """
    LangGraph 1.0 风格的 HITL 节点（使用 interrupt）

    - 第一次运行到这里：
        * 构造 req（人审请求 payload）
        * 调用 interrupt(req) → 图暂停，req 通过 AG-UI 事件流返回给前端
        * 注意：此时不会执行到下面解析 ui_resp 的代码
    - 前端调用 resolve(...) 回复后：
        * 再次运行到这里，interrupt(req) 返回 ui_resp
        * 使用 domain.review.normalize_review_response 做 JSON 解析 & 类型兜底
        * 然后根据 status 路由下一步
    """
    # 1) 构造人审请求 payload（纯领域逻辑在 domain.review 中）
    req = build_human_review_request(state)

    # 2) 中断：第一次会直接“抛出中断”，恢复时才会返回 ui_resp_raw
    ui_resp_raw = interrupt(req)

    # 3) 恢复时才会执行到这里：先把原始值打一下 log
    print(
        f"[DBG] human_review_gate resume thread={state.get('thread_id')} "
        f"resp_raw={ui_resp_raw!r} type={type(ui_resp_raw)}"
    )

    ui_resp, status, edited_code = normalize_review_response(ui_resp_raw)

    # 4) 根据人审结果路由

    # 4.1 审核通过 / 编辑后通过 → 进入回填+评价
    if status in ("approved", "edited"):
        final_code = edited_code or state.get("factor_code")
        return Command(
            goto="backfill_and_eval",
            update={
                "ui_request": req,
                "ui_response": ui_resp,
                "human_review_status": status,
                "human_edits": edited_code,
                "factor_code": final_code,
                "last_success_node": "human_review_gate",
                "error": None,
                "route": "backfill_and_eval",
            },
        )

    # 4.2 审核直接拒绝 → 直接结束
    if status == "rejected":
        return Command(
            goto="finish",
            update={
                "ui_request": req,
                "ui_response": ui_resp,
                "human_review_status": "rejected",
                "last_success_node": "human_review_gate",
                "error": None,
                "route": "finish",
            },
        )

    # 4.3 兜底：status 异常，也当 reject 处理
    return Command(
        goto="finish",
        update={
            "ui_request": req,
            "ui_response": ui_resp,
            "human_review_status": "rejected",
            "last_success_node": "human_review_gate",
            "error": {
                "node": "human_review_gate",
                "message": f"invalid ui_response status={status!r}",
            },
            "route": "finish",
        },
    )


def backfill_and_eval(state: FactorAgentState) -> Dict[str, Any] | Command:
    """
    历史回填与评价（mock），完成后进入入库。

    - domain.eval.compute_eval_metrics 负责生成指标
    """
    metrics = compute_eval_metrics()

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


def write_db(state: FactorAgentState) -> Dict[str, Any] | Command:
    """
    将评价结果入库（mock），然后进入结束节点。
    """
    name = state.get("factor_name") or "factor"
    metrics = state.get("eval_metrics", {}) or {}

    res = write_factor_and_metrics(name, metrics)

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
    """
    结束节点：简单跳转到 END，不再更新状态。

    - graph 层面有显式 finish -> END 的边
    """
    print(f"[DBG] finish thread={state.get('thread_id')}")
    return {}


"""
工作流节点实现（纯 Command 路由，方案 A）

节点：
- collect_spec: 收集用户描述
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
