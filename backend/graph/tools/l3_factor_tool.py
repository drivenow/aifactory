from __future__ import annotations

import ast
import traceback
import types
import sys
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from langchain_core.tools import tool


def build_mock_tick_data(length: int = 5) -> List[Dict[str, Any]]:
    """构造一个最小可用的逐笔盘口 mock 数据，避免空数据导致的 AttributeError。"""
    ticks: List[Dict[str, Any]] = []
    for i in range(length):
        ticks.append(
            {
                "Timestamp": 1718636219.81 + i * 0.001,
                "LastPrice": 47.5 + i * 0.01,
                "BidP0": 47.4 + i * 0.01,
                "AskP0": 47.6 + i * 0.01,
                "BidV0": 1000 + 10 * i,
                "AskV0": 1000 + 12 * i,
                "Volume": 100 + i,
                "Amount": 10000 + 50 * i,
            }
        )
    return ticks


L3_FACTORBASE_STUB = """
class FactorBase:
    def __init__(self, config=None, factorManager=None, marketDataManager=None):
        self.config = config or {}
        self.factorManager = factorManager
        self.marketDataManager = marketDataManager
        self._values = []
        self._mock_ticks = __mock_data__ or []

    def addFactorValue(self, v):
        try:
            self._values.append(v)
        except Exception:
            self._values.append(None)

    # ---- Tick ----
    def getPrevTick(self, field):
        if not self._mock_ticks:
            return None
        return self._mock_ticks[-1].get(field)

    def getPrevNTick(self, field, n):
        if not self._mock_ticks:
            return []
        return [t.get(field) for t in self._mock_ticks[-int(n):]]

    def getPrevSecTick(self, field, n_seconds, end_timestamp=None):
        return self.getPrevNTick(field, 1)

    # ---- Order / Trade / Cancel (最小 stub，返回空或最近值) ----
    def getPrevOrder(self, field=None):
        return None

    def getPrevNOrder(self, field, n):
        return []

    def getPrevSecOrder(self, field, n_seconds, end_timestamp=None):
        return []

    def getPrevTrade(self, field=None):
        return None

    def getPrevNTrade(self, field, n):
        return []

    def getPrevSecTrade(self, field, n_seconds, end_timestamp=None):
        return []

    def getPrevCancel(self, field=None):
        return None

    def getPrevNCancel(self, field, n):
        return []

    def getPrevSecCancel(self, field, n_seconds, end_timestamp=None):
        return []

    # ---- 时间/采样 ----
    def get_sample_flag(self):
        return 1

    def get_sample_1s_flag(self):
        return 1

    def get_timestamp(self):
        if not self._mock_ticks:
            return 0
        return self._mock_ticks[-1].get("Timestamp", 0)
"""


def _syntax_check(code: str) -> Dict[str, Any]:
    """AST 语法与基本结构检查。"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"ok": False, "error": f"SyntaxError: {e}"}

    has_factor_class = False
    has_calculate = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "FactorBase":
                    has_factor_class = True
        if isinstance(node, ast.FunctionDef) and node.name == "calculate":
            has_calculate = True
    if not has_factor_class:
        return {"ok": False, "error": "No class inheriting FactorBase found"}
    if not has_calculate:
        return {"ok": False, "error": "No calculate(self) method found"}
    return {"ok": True, "error": None}


def _install_factorbase_stub(ns: Dict[str, Any], mock_data: List[Dict[str, Any]]):
    """在 namespace 中安装 FactorBase stub 以及 L3FactorFrame 模块别名。"""
    ns["__mock_data__"] = mock_data
    exec(L3_FACTORBASE_STUB, ns, ns)

    # 安装模块别名，支持 from L3FactorFrame.FactorBase import FactorBase
    fb_cls = ns["FactorBase"]
    l3_module = types.ModuleType("L3FactorFrame")
    fb_module = types.ModuleType("L3FactorFrame.FactorBase")
    fb_module.FactorBase = fb_cls
    l3_module.FactorBase = fb_module
    sys.modules["L3FactorFrame"] = l3_module
    sys.modules["L3FactorFrame.FactorBase"] = fb_module


def _mock_run(code: str, mock_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """受限 namespace 下执行一次 calculate，自检可运行性。"""
    mock_ticks = mock_data or build_mock_tick_data()
    ns: Dict[str, Any] = {
        "np": np,
        "numpy": np,
        "pd": pd,
        "pandas": pd,
        "__builtins__": __builtins__,
    }
    try:
        _install_factorbase_stub(ns, mock_ticks)
        exec(code, ns, ns)

        fb_cls = ns.get("FactorBase")
        factor_cls = None
        for v in ns.values():
            if isinstance(v, type) and fb_cls and issubclass(v, fb_cls) and v is not fb_cls:
                factor_cls = v
                break
        if factor_cls is None:
            return {"ok": False, "error": "No FactorBase subclass found", "result": None}

        inst = factor_cls(config=None, factorManager=None, marketDataManager=None)
        inst.calculate()
        values = getattr(inst, "_values", [])
        return {"ok": True, "error": None, "result": values}
    except Exception:
        return {"ok": False, "error": traceback.format_exc(), "result": None}


@tool("l3_syntax_check")
def l3_syntax_check(code: str) -> Dict[str, Any]:
    """对 L3 因子代码做语法与基本结构检查。"""
    return _syntax_check(code)


@tool("l3_mock_run")
def l3_mock_run(code: str) -> Dict[str, Any]:
    """
    在本地 stub 的 L3 环境下执行一次 calculate，做最基本的可运行性检查。
    返回: {"ok": bool, "error": str | None, "result": list | None}
    """
    syntax = _syntax_check(code)
    if not syntax["ok"]:
        return {"ok": False, "error": syntax["error"], "result": None}
    return _mock_run(code)


__all__ = [
    "l3_syntax_check",
    "l3_mock_run",
    "build_mock_tick_data",
    "_syntax_check",
    "_mock_run",
]
