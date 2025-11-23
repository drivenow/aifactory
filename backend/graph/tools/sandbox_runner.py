import traceback
import os
import pandas as pd
import numpy as np

def run_code(code: str, entry: str = "run_factor", args: dict | None = None) -> dict:
    """执行代码并返回标准化结构"""
    try:
        # 创建单一命名空间
        ns = {
            "__builtins__": __builtins__,
            "pd": pd, "pandas": pd, "np": np, "numpy": np, "os": os,
        }
        
        # 执行代码
        exec(code, ns, ns)
        
        # 获取入口函数并执行
        fn = ns[entry]
        
        if args and isinstance(args, dict):
            a = args.get("args") or []
            kw = args.get("kwargs") or {}
            res = fn(*a, **kw)
        else:
            res = fn("2020-01-01", "2020-01-10", ["A"]) 
            
        return {"success": True, "result": res}
        
    except Exception as e:
        return {"success": False, "traceback": traceback.format_exc()}