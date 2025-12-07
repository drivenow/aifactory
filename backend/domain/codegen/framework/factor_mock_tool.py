from typing import Dict
import ast
from typing import Dict, Any

FACTOR_TEMPLATE = """
# Factor: {factor_name}
# Description: {user_spec}

import pandas as pd


def load_data(start, end, universe):
    return pd.DataFrame({{'close': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]}})

def compute_factor(df: pd.DataFrame) -> pd.Series:
{factor_body}

def run_factor(start, end, universe):
    df = load_data(start, end, universe)
    return compute_factor(df)
"""

def semantic_check_factor_code(factor_code: str) -> Dict[str, Any]:
    """
    对生成的因子代码进行语义检查，确保其可执行且符合预期结构。

    参数：
    - factor_code: 完整的因子代码字符串

    返回：
    - dict: 包含检查结果，格式如下：
        {
            "valid": bool,          # 是否通过检查
            "message": str,         # 检查结果说明
            "issues": List[str]     # 具体问题列表（如存在）
        }
    """
    issues = []

    try:
        # 检查语法合法性
        tree = ast.parse(factor_code)
    except SyntaxError as e:
        return {
            "valid": False,
            "message": "代码存在语法错误",
            "issues": [f"语法错误: {e}"]
        }

    # 检查是否包含必要函数
    required_functions = {"load_data", "compute_factor", "run_factor"}
    found_functions = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            found_functions.add(node.name)

    missing = required_functions - found_functions
    if missing:
        issues.append(f"缺少必要函数: {', '.join(missing)}")

    # 检查 compute_factor 是否返回 pd.Series
    # 这里仅做静态检查：查看是否有 return 语句
    compute_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "compute_factor":
            compute_func = node
            break

    if compute_func:
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(compute_func))
        if not has_return:
            issues.append("compute_factor 函数缺少 return 语句")
    else:
        issues.append("未找到 compute_factor 函数定义")

    # 检查是否导入 pandas
    has_import_pandas = any(
        isinstance(node, ast.Import) and any(alias.name == "pandas" for alias in node.names) or
        isinstance(node, ast.ImportFrom) and node.module == "pandas"
        for node in ast.walk(tree)
    )
    if not has_import_pandas:
        issues.append("未导入 pandas 模块")

    if issues:
        return {
            "valid": False,
            "message": "代码未通过语义检查",
            "issues": issues
        }
    else:
        return {
            "valid": True,
            "message": "代码通过语义检查",
            "issues": []
        }


def render_factor_code(factor_name: str, user_spec: str, factor_body: str) -> str:
    """渲染因子模板

    参数：
    - factor_name: 因子名称标识
    - user_spec: 用户自然语言描述
    - factor_body: 计算主体代码（需正确缩进）
    """
    return FACTOR_TEMPLATE.format(
        factor_name=factor_name,
        user_spec=user_spec,
        factor_body=factor_body,
    )


def simple_factor_body_from_spec(user_spec: str) -> str:
    """根据描述生成简易因子主体（mock）

    说明：
    - 识别“滚动均值/MA”等关键词，返回相应计算逻辑
    - 未识别时返回 `raise NotImplementedError`，便于触发 run_factor_dryrun 失败与人审
    """
    s = user_spec.lower()
    if "moving average" in s or "ma" in s or "滚动均值" in s or "均值" in s:
        return (
            "    window = 5\n"
            "    price = df['close']\n"
            "    return price.rolling(window).mean()\n"
        )
    if "momentum" in s or "动量" in s:
        return (
            "        lookback = 5\n"
            "        price = df['close'] if isinstance(df, dict) else df['close']\n"
            "        return price.pct_change(lookback)\n"
        )
    return "        raise NotImplementedError\n"
"""
因子模板与渲染工具

该模块提供统一的因子代码模板 FACTOR_TEMPLATE，以及将因子名/描述/主体填入模板的渲染函数。
同时提供一个基于用户描述的简易主体生成器（mock），用于 MVP 阶段的快速演示。
"""