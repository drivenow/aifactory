# nodes.py
from __future__ import annotations

from typing import Dict, Any, Optional

from pydantic import BaseModel, Field
from langgraph.graph import END
# nodes.py 顶部
from langgraph.types import Command, interrupt


from .state import FactorAgentState
from .tools.factor_template import render_factor_code, simple_factor_body_from_spec
from .tools import mock_evals
from .tools.sandbox_runner import run_code

RETRY_MAX = 5  # 超过该次数强制进入 HITL


# -------------------------
# Pydantic action schemas
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
            update={**base_update, "should_interrupt": True, "route": "human_review_gate"},
        )

    return Command(
        goto=target_if_retry,
        update={**base_update, "route": target_if_retry},
    )


# -------------------------
# Nodes
# -------------------------

def collect_spec(state: FactorAgentState) -> Command:
    """收集用户因子描述与名称，并进入代码生成阶段"""
    spec = state.get("user_spec")
    if not spec:
        msgs = state.get("messages", [])
        if isinstance(msgs, list) and msgs:
            last = msgs[-1]
            if isinstance(last, dict):
                spec = last.get("content", "") or str(last)
            else:
                c = getattr(last, "content", None)
                if c is None:
                    c = getattr(last, "text", None)
                spec = c if c is not None else str(last)
        else:
            spec = ""

    name = state.get("factor_name") or "factor"

    print(
        f"[DBG] collect_spec thread={state.get('thread_id')} "
        f"spec_len={len(spec) if isinstance(spec, str) else 0} name={name}"
    )

    update = {
        "user_spec": spec,
        "factor_name": name,
        "retry_count": int(state.get("retry_count", 0)),
        "last_success_node": "collect_spec",
        "error": None,
        "route": "gen_code_react",
    }
    return Command(goto="gen_code_react", update=update)


def gen_code_react(state: FactorAgentState) -> Command:
    """按模板生成因子代码（ReAct 代理也可以在这里替换/接入）"""
    try:
        spec = state.get("user_spec") or ""
        if not spec:
            raise ValueError("missing user_spec in state")

        name = state.get("factor_name") or "factor"
        body = simple_factor_body_from_spec(spec)
        code = render_factor_code(name, spec, body)

        print(
            f"[DBG] gen_code_react thread={state.get('thread_id')} "
            f"code_len={len(code) if isinstance(code, str) else 0}"
        )

        action = CodeGenAction(factor_code=code)

        return Command(
            goto="dryrun",
            update={
                "factor_code": action.factor_code,
                "last_success_node": "gen_code_react",
                "error": None,
                "route": "dryrun",
            },
        )

    except Exception as e:
        print(f"[DBG] gen_code_react error thread={state.get('thread_id')} msg={str(e)}")
        return _route_retry_or_hitl(
            state,
            {
                "error": {"node": "gen_code_react", "message": str(e)},
                "last_success_node": "gen_code_react",
            },
            target_if_retry="gen_code_react",
        )


def dryrun(state: FactorAgentState) -> Command:
    """沙盒试运行 `run_factor` 入口，成功则进入语义检查，失败则走重试/HITL"""
    code = state.get("factor_code", "") or ""
    result = run_code(
        code,
        entry="run_factor",
        args={"args": ["2020-01-01", "2020-01-10", ["A"]], "kwargs": {}},
    )
    success = bool(result.get("success"))

    print(
        f"[DBG] dryrun thread={state.get('thread_id')} "
        f"success={success} retry_count={state.get('retry_count')}"
    )

    if success:
        return Command(
            goto="semantic_check",
            update={
                "dryrun_result": {"success": True, "stdout": result.get("stdout", "")},
                "last_success_node": "dryrun",
                "error": None,
                "route": "semantic_check",
            },
        )

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


def semantic_check(state: FactorAgentState) -> Command:
    """语义一致性检查：要求 spec、code 存在且 dryrun 成功"""
    spec = state.get("user_spec", "") or ""
    code = state.get("factor_code", "") or ""
    dry_ok = bool(state.get("dryrun_result", {}).get("success"))

    ok = bool(spec) and bool(code) and dry_ok
    result = SemanticCheckResult(ok=ok)

    print(f"[DBG] semantic_check thread={state.get('thread_id')} ok={result.ok}")

    if result.ok:
        return Command(
            goto="human_review_gate",
            update={
                "semantic_check": {"pass": True},
                "last_success_node": "semantic_check",
                "error": None,
                "route": "human_review_gate",
            },
        )

    return _route_retry_or_hitl(
        state,
        {
            "semantic_check": {"pass": False, "reason": "spec/code/dryrun mismatch"},
            "error": {"node": "semantic_check", "message": "semantic_check failed"},
            "last_success_node": "semantic_check",
        },
        target_if_retry="gen_code_react",
    )
def human_review_gate(state: FactorAgentState) -> Command:
    """
    HITL 节点（LangGraph 1.0 风格）

    - 第一次执行到这里：调用 interrupt(req) → 图暂停，返回给前端一个中断事件
    - 前端在人审 UI 里点 approve/edit/reject 后，通过 ag-ui 回传 ui_response
    - 第二次执行到这里：interrupt(req) 会直接返回这次 ui_response，继续走后续逻辑
    """

    req = {
        "type": "code_review",
        "title": "Review generated factor code",
        "code": state.get("factor_code", "") or "",
        "actions": ["approve", "edit", "reject"],
        "retry_count": int(state.get("retry_count", 0)),
    }

    # 在 state 里也记一份，方便前端直接从 agentState 读取
    # 第一次跑到这里时，下面这句不会被真正“执行完”，因为 interrupt 会先中断返回
    ui_resp = interrupt(req)

    # 只有“恢复运行”的时候，才会执行到下面这些代码
    print(
        f"[DBG] human_review_gate resume thread={state.get('thread_id')} "
        f"resp={ui_resp}"
    )

    status = ui_resp.get("status") or ui_resp.get("human_review_status")
    edited_code = ui_resp.get("edited_code") or ui_resp.get("factor_code")

    if status in ("approved", "edited"):
        final_code = edited_code or state.get("factor_code")

        return Command(
            goto="backfill_and_eval",
            update={
                "ui_request": req,              # 方便前端展示上下文
                "ui_response": ui_resp,         # 记录人审结果
                "human_review_status": status,
                "human_edits": edited_code,
                "factor_code": final_code,
                "last_success_node": "human_review_gate",
                "error": None,
                "route": "backfill_and_eval",
            },
        )

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

    # 万一前端传了个奇怪的 status，当 reject 处理
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


def backfill_and_eval(state: FactorAgentState) -> Command:
    """历史回填与评价（mock），完成后进入入库"""
    ic = mock_evals.factor_ic_mock()
    to = mock_evals.factor_turnover_mock()
    gp = mock_evals.factor_group_perf_mock()
    metrics = {"ic": ic, "turnover": to, "group_perf": gp}

    print(
        f"[DBG] backfill_and_eval thread={state.get('thread_id')} "
        f"metrics_keys={list(metrics.keys())}"
    )

    return Command(
        goto="write_db",
        update={
            "eval_metrics": metrics,
            "last_success_node": "backfill_and_eval",
            "error": None,
            "route": "write_db",
        },
    )


def write_db(state: FactorAgentState) -> Command:
    """将评价结果入库（mock），然后进入结束节点"""
    name = state.get("factor_name") or "factor"
    metrics = state.get("eval_metrics", {}) or {}
    res = mock_evals.write_factor_and_metrics_mock(name, metrics)

    print(
        f"[DBG] write_db thread={state.get('thread_id')} "
        f"status={res.get('status', 'unknown')}"
    )

    return Command(
        goto="finish",
        update={
            "db_write_status": res.get("status", "success"),
            "last_success_node": "write_db",
            "error": None,
            "route": "finish",
        },
    )


def finish(state: FactorAgentState) -> Command:
    """结束节点"""
    print(f"[DBG] finish thread={state.get('thread_id')}")
    return Command(goto=END, update={})


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
