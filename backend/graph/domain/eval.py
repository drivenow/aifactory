# backend/graph/domain/eval.py
from __future__ import annotations

from typing import Dict, Any
from pydantic import BaseModel, Field

from ..state import FactorAgentState, ViewBase
from ..tools import mock_evals


class EvalView(ViewBase):
    factor_name: str = "factor"
    eval_metrics: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    @ViewBase._wrap_from_state("EvalView.from_state")
    def from_state(cls, state: FactorAgentState) -> "EvalView":
        return cls(
            factor_name=state.get("factor_name") or "factor",
            eval_metrics=state.get("eval_metrics") or {},
        )


def compute_eval_metrics(state: FactorAgentState) -> Dict[str, Any]:
    view = EvalView.from_state(state)
    ic = mock_evals.factor_ic_mock()
    to = mock_evals.factor_turnover_mock()
    gp = mock_evals.factor_group_perf_mock()
    return {"ic": ic, "turnover": to, "group_perf": gp}


def write_factor_and_metrics(state: FactorAgentState) -> Dict[str, Any]:
    view = EvalView.from_state(state)
    metrics = view.eval_metrics
    return mock_evals.write_factor_and_metrics_mock(view.factor_name, metrics)      
