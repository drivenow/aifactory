from typing import Dict, Any

from .state import FactorAgentState
from .tools.factor_template import render_factor_code, simple_factor_body_from_spec
from .tools import mock_evals


def collect_spec(state: FactorAgentState) -> FactorAgentState:
    spec = state.get("user_spec") or ""
    name = state.get("factor_name") or "factor"
    return {"user_spec": spec, "factor_name": name, "retries_left": state.get("retries_left", 5), "last_success_node": "collect_spec"}


def gen_code_react(state: FactorAgentState) -> FactorAgentState:
    try:
        spec = state["user_spec"]
        name = state.get("factor_name") or "factor"
        body = simple_factor_body_from_spec(spec)
        code = render_factor_code(name, spec, body)
        return {"factor_code": code, "last_success_node": "gen_code_react"}
    except Exception as e:
        return {"error": {"node": "gen_code_react", "message": str(e)}}


def dryrun(state: FactorAgentState) -> FactorAgentState:
    code = state.get("factor_code", "")
    if "raise NotImplementedError" in code:
        return {"dryrun_result": {"success": False}, "retries_left": max(0, state.get("retries_left", 0) - 1), "error": {"node": "dryrun", "message": "factor not implemented"}}
    return {"dryrun_result": {"success": True}, "last_success_node": "dryrun"}


def semantic_check(state: FactorAgentState) -> FactorAgentState:
    spec = state.get("user_spec", "")
    code = state.get("factor_code", "")
    ok = bool(spec) and bool(code)
    return {"semantic_check": {"pass": ok}, "last_success_node": "semantic_check" if ok else state.get("last_success_node")}


def error_resume_router(state: FactorAgentState) -> str:
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
    retries = state.get("retries_left", 0)
    return {"retries_left": max(0, retries - 1)}


def human_review_gate(state: FactorAgentState) -> FactorAgentState:
    status = state.get("human_review_status") or "approved"
    return {"human_review_status": status, "last_success_node": "human_review_gate"}


def backfill_and_eval(state: FactorAgentState) -> FactorAgentState:
    ic = mock_evals.factor_ic_mock()
    to = mock_evals.factor_turnover_mock()
    gp = mock_evals.factor_group_perf_mock()
    metrics = {"ic": ic, "turnover": to, "group_perf": gp}
    return {"eval_metrics": metrics, "last_success_node": "backfill_and_eval"}


def write_db(state: FactorAgentState) -> FactorAgentState:
    name = state.get("factor_name") or "factor"
    metrics = state.get("eval_metrics", {})
    res = mock_evals.write_factor_and_metrics_mock(name, metrics)
    return {"db_write_status": res.get("status", "success"), "last_success_node": "write_db"}


def finish(state: FactorAgentState) -> FactorAgentState:
    return {}