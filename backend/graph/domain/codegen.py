# backend/graph/domain/codegen.py
from __future__ import annotations

from typing import Dict, Any

from ..tools.factor_template import (
    render_factor_code,
    simple_factor_body_from_spec,
)
from ..tools.sandbox_runner import run_code


def generate_factor_code_from_spec(name: str, spec: str) -> str:
    """
    根据用户的自然语言 spec 生成模板化因子代码。

    目前是简单模板：
    - simple_factor_body_from_spec: 生成函数 body
    - render_factor_code: 根据因子名 + 描述 + body 渲染出完整 Python 代码
    """
    body = simple_factor_body_from_spec(spec)
    code = render_factor_code(name, spec, body)
    return code


def run_factor_dryrun(code: str) -> Dict[str, Any]:
    """
    在沙盒中试运行因子代码，调用入口 run_factor。

    返回值格式约定：
    - success: bool
    - stdout / stderr / traceback: 字符串
    """
    result = run_code(
        code,
        entry="run_factor",
        args={"args": ["2020-01-01", "2020-01-10", ["A"]], "kwargs": {}},
    )
    # 保持原始结构，节点里自己取字段
    return result


def is_semantic_check_ok(spec: str, code: str, dryrun_success: bool) -> bool:
    """
    一个非常简单的“语义检查”规则：

    - spec 非空
    - code 非空
    - dryrun_success 为 True
    """
    return bool(spec) and bool(code) and bool(dryrun_success)
