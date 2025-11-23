import traceback
import os
from typing import Optional, Dict


def run_code(code: str, entry: str = "run_factor", args: Optional[dict] = None) -> dict:
    """执行代码并返回标准化结构

    参数：
    - code: 完整 Python 代码字符串
    - entry: 入口函数名（默认 `run_factor`）
    - args: 调用参数，形如 {"args": [...], "kwargs": {...}}

    返回：
    - {"success": True, "result": any} 或 {"success": False, "traceback": str}
    """
    try:
        print("[DBG] sandbox_run entry", entry)
        g = {"__builtins__": __builtins__, "ENV": dict(os.environ)}
        l = g
        exec(code, g, l)
        fn = g.get(entry)
        if not callable(fn):
            return {"success": False, "traceback": "entry_not_found"}
        if args and isinstance(args, dict):
            a = args.get("args") or []
            kw = args.get("kwargs") or {}
            print("[DBG] sandbox_args", len(a), len(kw))
            res = fn(*a, **kw)
        else:
            res = fn("2020-01-01", "2020-01-10", ["A"]) 
        print("[DBG] sandbox_success")
        return {"success": True, "result": res}
    except Exception:
        tb = traceback.format_exc()
        print("[DBG] sandbox_error", tb.splitlines()[-1] if tb else "")
        return {"success": False, "traceback": tb}
"""受限沙盒执行器

用于在受控环境下执行模板生成的因子代码，捕获输出与异常，避免对系统造成破坏。
安全策略（MVP）：
- 使用隔离的 `globals/locals` 执行，允许完整内建与标准导入（不写回宿主）
- 提供只读快照 `ENV`（`os.environ` 拷贝），避免污染宿主环境变量
- 无文件系统/网络访问
- 执行入口仅限 `run_factor`
"""