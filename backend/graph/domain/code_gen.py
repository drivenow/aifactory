from __future__ import annotations

"""
Thin compatibility layer exporting codegen submodules.
Future changes should happen under backend/graph/domain/codegen/.
"""

from .codegen import (
    CodeGenView,
    CodeMode,
    SemanticCheckResult,
    DryrunResult,
    generate_factor_code_from_spec,
    run_factor,
    run_factor_dryrun,
    is_semantic_check_ok,
    build_l3_codegen_agent,
    create_agent,
)

# For test hooks that monkeypatch _L3_AGENT
from .codegen import agent as _agent_mod  # type: ignore


def _get_L3_AGENT():
    return _agent_mod._L3_AGENT


def _set_L3_AGENT(val):
    _agent_mod._L3_AGENT = val


# Expose mutable reference for monkeypatch (pytest)
class _L3AgentProxy:
    def __call__(self):
        return _get_L3_AGENT()

    def set(self, val):
        _set_L3_AGENT(val)


_L3_AGENT = _L3AgentProxy()

__all__ = [
    "CodeGenView",
    "CodeMode",
    "SemanticCheckResult",
    "DryrunResult",
    "generate_factor_code_from_spec",
    "run_factor",
    "run_factor_dryrun",
    "is_semantic_check_ok",
    "_L3_AGENT",
    "build_l3_codegen_agent",
    "create_agent",
]
