from typing import Dict, Any
from pydantic import BaseModel, Field

# try:
from global_state import FactorAgentState, ViewBase
# except (ImportError, ValueError):  # pragma: no cover
#     class ViewBase(BaseModel):
#         @classmethod
#         def _wrap_from_state(cls, name):
#             def deco(func):
#                 return func
#             return deco

#     class FactorAgentState(dict):
#         pass

class EvalView(ViewBase):
    factor_name: str = "factor"
    eval_type: str = "mock"
    eval_metrics: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    @ViewBase._wrap_from_state("EvalView.from_state")
    def from_state(cls, state: FactorAgentState) -> "EvalView":
        return cls(
            factor_name=state.get("factor_name") or "factor",
            eval_type=state.get("eval_type") or "mock",
            eval_metrics=state.get("eval_metrics") or {},
        )