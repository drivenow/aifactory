# backend/domain/__init__.py
import sys
import os
domain_sys_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
# 添加所有第三库的调用到这个文件
thirdparty_path = os.path.join(domain_sys_path, "../thirdparty")
sys.path.append(thirdparty_path)
print("domain_sys_path:", domain_sys_path)

from .codegen import (
    CodeGenView,
    CodeMode,
    SemanticCheckResult,
    DryrunResult,
    generate_factor_code_from_spec,
    run_factor,
    run_factor_dryrun,
    check_semantics_static,
    build_l3_codegen_agent,
    create_agent,
)

from .evaluate import compute_eval_metrics, write_factor_and_metrics
from .human_review import build_human_review_request, normalize_review_response
from .logic_gen import extract_spec_and_name

__all__ = [
    "CodeGenView",
    "CodeMode",
    "SemanticCheckResult",
    "DryrunResult",
    "generate_factor_code_from_spec",
    "run_factor",
    "run_factor_dryrun",
    "check_semantics_static",
    "build_l3_codegen_agent",
    "create_agent",
    "compute_eval_metrics",
    "write_factor_and_metrics",
    "build_human_review_request",
    "normalize_review_response",
    "extract_spec_and_name",
]
