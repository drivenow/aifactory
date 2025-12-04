from __future__ import annotations

from .tools.factor_template import (
    render_factor_code,
    simple_factor_body_from_spec,
)

from .agent import invoke_l3_agent
from .view import CodeGenView, CodeMode


def generate_l3_factor_code(view: CodeGenView) -> str:
    return invoke_l3_agent(view)


def generate_factor_code_from_spec(state) -> str:
    view = CodeGenView.from_state(state)
    if view.code_mode == CodeMode.L3_PY or view.code_mode == "l3_py":
        return generate_l3_factor_code(view)

    body = simple_factor_body_from_spec(view.user_spec)
    return render_factor_code(view.factor_name, view.user_spec, body)



if __name__ == "__main__":
    view = CodeGenView(
        factor_name="TestFactor",
        user_spec="计算股票的简单移动平均线",
        code_mode=CodeMode.L3_PY,
    )
    code = generate_l3_factor_code(view)
    print(code)
