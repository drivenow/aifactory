from typing import Dict, Any

from pydantic import BaseModel, Field
from langgraph.types import Command
from langgraph.graph import END

from .state import FactorAgentState
from .tools.factor_template import render_factor_code, simple_factor_body_from_spec
from .tools import mock_evals
from .tools.sandbox_runner import run_code

RETRY_MAX = 5  # 超过该次数强制进入 HITL

class IntentAction(BaseModel):
    """意图抽取动作输出：因子名与约束"""
    human_input: bool = False
    message: str | None = None
    factor_name: str | None = None
    constraints: Dict[str, Any] = Field(default_factory=dict)

class CodeGenAction(BaseModel):
    """代码生成动作输出：模板化因子代码与反思备注"""
    human_input: bool = False
    message: str | None = None
    factor_code: str | None = None
    reflect_notes: str | None = None

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
    reason: str | None = None

class HumanReviewAction(BaseModel):
    """人审结果：审批/编辑/驳回"""
    status: str  # approved/edited/rejected
    edited_code: str | None = None

class BackfillAction(BaseModel):
    """历史回填动作输出：预览统计与任务 ID"""
    ok: bool
    job_id: str | None = None
    preview_stats: Dict[str, Any] = Field(default_factory=dict)

class EvalAction(BaseModel):
    """评价动作输出：各项评价指标"""
    ok: bool
    metrics: Dict[str, Any] = Field(default_factory=dict)

class PersistAction(BaseModel):
    """入库动作输出：目标地址与写入行数"""
    ok: bool
    uri: str | None = None
    rows_written: int = 0


def _route_retry_or_hitl(state: FactorAgentState, update: Dict[str, Any], target_if_retry: str = "gen_code_react") -> Command:
    """统一的重试/HITL 路由策略

    - 将 `retry_count` +1，`retries_left` -1
    - 当 `retry_count >= RETRY_MAX` 时，强制进入 HITL（should_interrupt=True）并跳转到 `human_review_gate`
    - 否则跳转到 `target_if_retry`（通常为重新生成代码的节点）
    """
    rc = int(state.get("retry_count", 0)) + 1
    rl = max(0, int(state.get("retries_left", 0)) - 1)
    if rc >= RETRY_MAX:
        return Command(goto="human_review_gate", update={**update, "retry_count": rc, "retries_left": rl, "should_interrupt": True})
    return Command(goto=target_if_retry, update={**update, "retry_count": rc, "retries_left": rl})


def collect_spec(state: FactorAgentState):
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
    update = {"user_spec": spec, "factor_name": name, "retries_left": state.get("retries_left", 5), "last_success_node": "collect_spec", "error": None, "route": "gen_code_react"}
    return Command(goto="gen_code_react", update=update)


def gen_code_react(state: FactorAgentState):
    """按模板生成因子代码（ReAct 代理在此处接入）"""
    try:
        spec = state["user_spec"]
        name = state.get("factor_name") or "factor"
        body = simple_factor_body_from_spec(spec)
        code = render_factor_code(name, spec, body)
        action = CodeGenAction(factor_code=code)
        return Command(goto="dryrun", update={"factor_code": action.factor_code, "last_success_node": "gen_code_react", "error": None, "route": "dryrun"})
    except Exception as e:
        return _route_retry_or_hitl(state, {"error": {"node": "gen_code_react", "message": str(e)}, "route": "gen_code_react"}, target_if_retry="gen_code_react")


def dryrun(state: FactorAgentState):
    """沙盒试运行 `run_factor` 入口，成功则进入语义检查，失败则走重试/HITL"""
    code = state.get("factor_code", "")
    result = run_code(code, entry="run_factor", args={"args": ["2020-01-01", "2020-01-10", ["A"]], "kwargs": {}})
    if result.get("success"):
        return Command(goto="semantic_check", update={"dryrun_result": {"success": True}, "last_success_node": "dryrun", "error": None, "route": "semantic_check"})
    return _route_retry_or_hitl(
        state,
        {"dryrun_result": {"success": False, "traceback": result.get("traceback")}, "error": {"node": "dryrun", "message": "failed"}, "route": "gen_code_react"},
        target_if_retry="gen_code_react",
    )


def semantic_check(state: FactorAgentState):
    """语义一致性检查：要求 `spec`、`code` 存在且 `dryrun` 成功"""
    spec = state.get("user_spec", "")
    code = state.get("factor_code", "")
    ok = bool(spec) and bool(code) and bool(state.get("dryrun_result", {}).get("success"))
    result = SemanticCheckResult(ok=ok)
    if result.ok:
        return Command(goto="human_review_gate", update={"semantic_check": {"pass": True}, "last_success_node": "semantic_check", "error": None, "route": "human_review_gate"})
    return _route_retry_or_hitl(state, {"semantic_check": {"pass": False}, "error": None, "route": "gen_code_react"}, target_if_retry="gen_code_react")


def error_resume_router(state: FactorAgentState) -> str:
    # 兼容层：旧式条件路由函数，已不再被图编排使用
    err = state.get("error")
    dry = state.get("dryrun_result", {})
    if err or (dry and not dry.get("success")):
        last = state.get("last_success_node")
        retries = state.get("retries_left", 0)
        if dry and not dry.get("success"):
            if retries > 0:
                return "resume_to_gen_code_react"
            return "resume_to_human_review_gate"
        mapping = {
            "collect_spec": "resume_to_gen_code_react",
            "gen_code_react": "resume_to_dryrun",
            "dryrun": "resume_to_semantic_check",
            "semantic_check": "resume_to_human_review_gate",
            "human_review_gate": "resume_to_backfill",
            "backfill_and_eval": "resume_to_write_db",
        }
        return mapping.get(last, "resume_to_gen_code_react")
    return "pass"


def backtrack_dispatch(state: FactorAgentState) -> str:
    return "collect_spec"


def react_retry_router(state: FactorAgentState) -> str:
    # 兼容层：旧式条件路由函数，已不再被图编排使用
    sem = state.get("semantic_check", {})
    dry = state.get("dryrun_result", {})
    retries = state.get("retries_left", 0)
    pass_ok = sem.get("pass") and dry.get("success")
    if pass_ok:
        return "pass"
    if retries > 0:
        return "retry"
    return "pass"


def react_retry_update(state: FactorAgentState) -> FactorAgentState:
    """兼容层：旧式重试计数更新（不建议在纯 Command 路由中使用）"""
    retries = state.get("retries_left", 0)
    return {"retries_left": max(0, retries - 1), "error": None}


def human_review_gate(state: FactorAgentState):
    # 尝试从最新用户消息解析 code_review_response
    msgs = state.get("messages", [])
    if isinstance(msgs, list) and msgs:
        last = msgs[-1]
        content = None
        if isinstance(last, dict):
            content = last.get("content")
        else:
            content = getattr(last, "content", None)
        if isinstance(content, str):
            if content.startswith("code_review_response:"):
                try:
                    import json
                    obj = json.loads(content.split(":", 1)[1])
                    status_candidate = obj.get("status")
                    edited_code = obj.get("edited_code")
                    if status_candidate in ("approved", "edited", "rejected"):
                        state["human_review_status"] = status_candidate
                        if status_candidate in ("approved", "edited") and edited_code:
                            state["human_edits"] = edited_code
                            state["factor_code"] = edited_code
                except Exception:
                    pass
            elif content in ("approved", "edited", "rejected"):
                state["human_review_status"] = content
    status = state.get("human_review_status") or "pending"
    if status in ("approved", "edited"):
        code = state.get("human_edits") or state.get("factor_code")
        update = {"ui_request": None, "human_review_status": status, "factor_code": code, "last_success_node": "human_review_gate", "error": None, "route": "backfill_and_eval"}
        return Command(goto="backfill_and_eval", update=update)
    if status == "rejected":
        return Command(goto="finish", update={"ui_request": None, "human_review_status": status, "last_success_node": "human_review_gate", "error": None, "route": "finish"})
    req = {"type": "code_review", "code": state.get("factor_code", ""), "actions": ["approve", "edit", "reject"]}
    return {"ui_request": req, "should_interrupt": True, "route": "human_review_gate"}


def backfill_and_eval(state: FactorAgentState):
    """历史回填与评价（mock），完成后进入入库"""
    ic = mock_evals.factor_ic_mock()
    to = mock_evals.factor_turnover_mock()
    gp = mock_evals.factor_group_perf_mock()
    metrics = {"ic": ic, "turnover": to, "group_perf": gp}
    return Command(goto="write_db", update={"eval_metrics": metrics, "last_success_node": "backfill_and_eval", "error": None, "route": "write_db"})


def write_db(state: FactorAgentState):
    """将评价结果入库（mock），然后进入结束节点"""
    name = state.get("factor_name") or "factor"
    metrics = state.get("eval_metrics", {})
    res = mock_evals.write_factor_and_metrics_mock(name, metrics)
    return Command(goto="finish", update={"db_write_status": res.get("status", "success"), "last_success_node": "write_db", "error": None, "route": "finish"})


def finish(state: FactorAgentState):
    return Command(goto=END, update={})
"""工作流节点实现（纯 Command 路由）

该模块实现因子编码助手的各阶段节点：收集规格、代码生成、试运行、语义检查、
人审、历史回填与评价、入库、结束。节点统一返回 `Command(goto=..., update=...)` 控制路由，
并通过 `retry_count` + `retries_left` 实现重试与强制进入 HITL 的策略。
"""