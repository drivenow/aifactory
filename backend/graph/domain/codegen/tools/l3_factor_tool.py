from __future__ import annotations

import ast
import traceback
import sys
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool

# --- Mocks & Stubs ---

def build_mock_tick_data(length: int = 5) -> List[Dict[str, Any]]:
    ticks = []
    for i in range(length):
        ticks.append({
            "Timestamp": 1718636219.81 + i * 0.001,
            "LastPrice": 47.5 + i * 0.01,
            "Volume": 100 + i,
            "Amount": 10000 + 50 * i,
        })
    return ticks

L3_FACTORBASE_STUB = """
import math
import numpy as np

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
        if not self._mock_ticks: return None
        return self._mock_ticks[-1].get(field)

    def getPrevNTick(self, field, n):
        if not self._mock_ticks: return []
        return [t.get(field) for t in self._mock_ticks[-int(n):]]
    
    # ---- Helpers ----
    def get_sample_1s_flag(self):
        return 1
    
    def get_timestamp(self):
        if not self._mock_ticks: return 0
        return self._mock_ticks[-1].get("Timestamp", 0)

    def get_factor_instance(self, name):
        if self.factorManager:
            return self.factorManager.get_factor(name)
        return None

# Stub for FactorManager
class FactorManagerStub:
    def __init__(self):
        self.factors = {}
        self.mode = "SAMPLE_1S"
    
    def get_factor(self, name):
        return self.factors.get(name)
    
    def register_factor(self, name, obj):
        self.factors[name] = obj

# Stubs for NonFactors (populated with some dummy data to prevent IndexErrors)
class FactorSecTradeAggStub:
    def __init__(self):
        self.trade_buy_money_list = [1000.0] * 10
        self.trade_sell_money_list = [800.0] * 10
        self.trade_buy_num_list = [5] * 10
        self.trade_sell_num_list = [4] * 10
        self.trade_buy_volume_list = [100.0] * 10
        self.trade_sell_volume_list = [80.0] * 10

class FactorSecOrderBookStub:
    def __init__(self):
        self.last_px_list = [10.0] * 10
        self.high_px_list = [10.5] * 10
        self.low_px_list = [9.5] * 10
        self.open_px_list = [10.0] * 10
        self.total_volume_list = [1000.0] * 10
        self.total_turnover_list = [10000.0] * 10
        self.trades_list = [50] * 10
        self.bid_qty_list = [100.0] * 10
        self.bid_price_list = [9.9] * 10
        self.bid_order_nums_list = [10] * 10
        self.ask_qty_list = [100.0] * 10
        self.ask_price_list = [10.1] * 10
        self.ask_order_nums_list = [10] * 10

class FactorSecOrderAggStub:
    def __init__(self):
        self.num_bids_sec_list = [5] * 10
        self.num_asks_sec_list = [5] * 10
        self.qty_bids_sec_list = [50.0] * 10
        self.qty_asks_sec_list = [50.0] * 10
        self.net_volume_sec_list = [0.0] * 10
"""

# --- Internal Logic ---

def _syntax_check(code: str) -> Dict[str, Any]:
    try:
        tree = ast.parse(code)
        
        # Check for class definition inheriting from FactorBase
        has_factor_base = False
        class_name = ""
        has_calculate = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "FactorBase":
                        has_factor_base = True
                        class_name = node.name
                        
                        # Check for calculate method
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef) and item.name == "calculate":
                                has_calculate = True
        
        if not has_factor_base:
            return {"ok": False, "error": "Must define a class inheriting from FactorBase"}
        if not has_calculate:
            return {"ok": False, "error": f"Class {class_name} must define a 'calculate' method"}
            
        return {"ok": True, "class_name": class_name}
        
    except SyntaxError as e:
        return {"ok": False, "error": f"Syntax Error: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"Check failed: {str(e)}"}

import sys
import types
from contextlib import contextmanager

@contextmanager
def mock_l3_modules(factor_base_cls):
    """
    Temporarily mocks L3FactorFrame.FactorBase in sys.modules so that
    'from L3FactorFrame.FactorBase import FactorBase' works during exec().
    """
    # Create a dummy L3FactorFrame package
    l3_pkg = types.ModuleType("L3FactorFrame")
    
    # Mock FactorBase
    l3_fb_mod = types.ModuleType("L3FactorFrame.FactorBase")
    l3_fb_mod.FactorBase = factor_base_cls
    l3_pkg.FactorBase = l3_fb_mod
    
    # Mock tools.DecimalUtil
    l3_tools_pkg = types.ModuleType("L3FactorFrame.tools")
    l3_decimal_mod = types.ModuleType("L3FactorFrame.tools.DecimalUtil")
    l3_decimal_mod.isEqual = lambda a, b: abs(a - b) < 1e-9
    l3_decimal_mod.notEqual = lambda a, b: abs(a - b) >= 1e-9
    l3_tools_pkg.DecimalUtil = l3_decimal_mod
    l3_pkg.tools = l3_tools_pkg

    old_modules = {}
    keys_to_mock = [
        "L3FactorFrame", 
        "L3FactorFrame.FactorBase", 
        "L3FactorFrame.tools", 
        "L3FactorFrame.tools.DecimalUtil"
    ]
    
    for key in keys_to_mock:
        if key in sys.modules:
            old_modules[key] = sys.modules[key]
        
        if key == "L3FactorFrame":
            sys.modules[key] = l3_pkg
        elif key == "L3FactorFrame.FactorBase":
            sys.modules[key] = l3_fb_mod
        elif key == "L3FactorFrame.tools":
            sys.modules[key] = l3_tools_pkg
        elif key == "L3FactorFrame.tools.DecimalUtil":
            sys.modules[key] = l3_decimal_mod
        
    try:
        yield
    finally:
        # Restore original modules or remove mocks
        for key in keys_to_mock:
            if key in old_modules:
                sys.modules[key] = old_modules[key]
            else:
                del sys.modules[key]

def _mock_run(code: str) -> Dict[str, Any]:
    try:
        # 1. Prepare Namespace
        ns = {}
        
        # Inject mock data
        mock_ticks = build_mock_tick_data(10)
        ns["__mock_data__"] = mock_ticks
        
        # 2. Execute Stub Definitions
        exec(L3_FACTORBASE_STUB, ns, ns)
        
        # 3. Setup FactorManager and NonFactors
        fm = ns["FactorManagerStub"]()
        fm.register_factor("FactorSecTradeAgg", ns["FactorSecTradeAggStub"]())
        fm.register_factor("FactorSecOrderBook", ns["FactorSecOrderBookStub"]())
        fm.register_factor("FactorSecOrderAgg", ns["FactorSecOrderAggStub"]())
        
        # Grab the stub FactorBase class from ns
        FactorBaseStub = ns["FactorBase"]
        
        # 4. Execute User Code with Mocked Modules
        # We use the context manager to inject the stub class as the imported module
        with mock_l3_modules(FactorBaseStub):
            exec(code, ns, ns)
        
        # 5. Instantiate and Run
        # Find the user class (inheriting from FactorBase)
        target_cls = None
        
        # Note: The user's class inherits from the FactorBase in ns (which is FactorBaseStub)
        # OR from the one imported via 'from L3FactorFrame...'.
        # Since mock_l3_modules makes them the same class object (reference), isinstance checks should work
        # provided we check against FactorBaseStub.
        
        for name, obj in ns.items():
            if isinstance(obj, type) and issubclass(obj, FactorBaseStub) and obj is not FactorBaseStub:
                target_cls = obj
                break
        
        if not target_cls:
            return {"ok": False, "error": "No FactorBase subclass found in executed code."}
        
        # Instantiate
        # factorManager is passed as 2nd arg in stub __init__
        instance = target_cls(config={}, factorManager=fm, marketDataManager=None)
        
        # Run calculate
        # Call it a few times to simulate a loop if needed, but here just once
        instance.calculate()
        
        return {"ok": True, "result": instance._values}
        
    except Exception:
        return {"ok": False, "error": traceback.format_exc()}


# --- Tools ---

@tool("l3_syntax_check")
def l3_syntax_check(code: str) -> Dict[str, Any]:
    """
    Performs syntax and structural checks on L3 factor code.
    Ensures the code defines a class inheriting from FactorBase with a calculate method.
    """
    return _syntax_check(code)

@tool("l3_mock_run")
def l3_mock_run(code: str) -> Dict[str, Any]:
    """
    Executes the L3 factor code in a mock stub environment.
    Verifies runtime logic without external dependencies.
    Returns execution success status and the calculated values (or error traceback).
    """
    return _mock_run(code)
