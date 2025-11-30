import types
import sys
import pathlib

import pytest
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.graph.domain import code_gen


class DummyAgent:
    def __init__(self):
        self.invoked = False

    def invoke(self, inputs):
        self.invoked = True
        code = (
            "from L3FactorFrame.FactorBase import FactorBase\n\n"
            "class FactorTest(FactorBase):\n"
            "    def __init__(self, config, factorManager, marketDataManager):\n"
            "        super().__init__(config, factorManager, marketDataManager)\n"
            "    def calculate(self):\n"
            "        self.addFactorValue(1.0)\n"
        )
        msg = types.SimpleNamespace(type="assistant", content=code)
        return {"messages": [msg]}


def test_l3_codegen_and_dryrun(monkeypatch):
    dummy_agent = DummyAgent()

    # stub out llm + agent builder
    monkeypatch.setattr(code_gen, "_L3_AGENT", None)
    monkeypatch.setattr(code_gen, "get_llm", lambda: "llm")
    monkeypatch.setattr(code_gen, "create_agent", lambda llm, tools=None: dummy_agent)

    state = {
        "user_spec": "最近3笔买卖盘价量比对比",
        "factor_name": "FactorTest",
        "code_mode": "l3_py",
        "semantic_check": {},
    }

    code = code_gen.generate_factor_code_from_spec(state)

    assert "class FactorTest" in code
    assert "addFactorValue" in code
    assert dummy_agent.invoked is True

    # dryrun should succeed with mock runner
    run_res = code_gen.run_factor_dryrun({"factor_code": code, "code_mode": "l3_py"})
    assert run_res.get("success") is True

    # semantic check should pass
    ok, detail = code_gen.is_semantic_check_ok(
        {"factor_code": code, "code_mode": "l3_py", "factor_name": "FactorTest", "semantic_check": {}}
    )
    assert ok is True
    assert detail.get("pass") is True
