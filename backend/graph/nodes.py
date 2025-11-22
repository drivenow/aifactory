from typing import Dict, Any

from .state import FactorAgentState
from .tools.factor_template import render_factor_code, simple_factor_body_from_spec
from .tools import mock_evals


def collect_spec(state: FactorAgentState) -> FactorAgentState:
    spec = state.get("user_spec") or ""
    name = state.get("factor_name") or "factor"
    return {"user_spec": spec, "factor_name": name, "retries_left": state.get("retries_left", 5)}


def gen_code_react(state: FactorAgentState) -> FactorAgentState:
    spec = state["user_spec"]
    name = state.get("factor_name") or "factor"
    body = simple_factor_body_from_spec(spec)
    code = render_factor_code(name, spec, body)
    return {"factor_code": code}


def dryrun(state: FactorAgentState) -> FactorAgentState:
    return {"dryrun_result": {"success": True}}


def semantic_check(state: FactorAgentState) -> FactorAgentState:
    spec = state.get("user_spec", "")
    code = state.get("factor_code", "")
    ok = bool(spec) and bool(code)
    return {"semantic_check": {"pass": ok}}


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
    return {"human_review_status": status}


def backfill_and_eval(state: FactorAgentState) -> FactorAgentState:
    ic = mock_evals.factor_ic_mock()
    to = mock_evals.factor_turnover_mock()
    gp = mock_evals.factor_group_perf_mock()
    metrics = {"ic": ic, "turnover": to, "group_perf": gp}
    return {"eval_metrics": metrics}


def write_db(state: FactorAgentState) -> FactorAgentState:
    name = state.get("factor_name") or "factor"
    metrics = state.get("eval_metrics", {})
    res = mock_evals.write_factor_and_metrics_mock(name, metrics)
    return {"db_write_status": res.get("status", "success")}


def finish(state: FactorAgentState) -> FactorAgentState:
    return {}