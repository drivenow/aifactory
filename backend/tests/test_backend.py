import json

from backend.graph.graph import graph

def test_graph_success_flow():
    s = graph.invoke(
        {
            "user_spec": "5日滚动均值因子",
            "factor_name": "MA5",
            "retry_count": 0,
            "thread_id": "t-success",
            "run_id": "r-success",
        },
        config={"configurable": {"thread_id": "t-success"}},
    )
    assert s.get("db_write_status") == "success"
    assert s.get("last_success_node") == "write_db"
    assert isinstance(s.get("factor_code"), str) and len(s.get("factor_code")) > 0


def test_graph_failure_flow_human_review():
    s = graph.invoke(
        {
            "user_spec": "未知因子",
            "factor_name": "X",
            "retry_count": 1,
            "thread_id": "t-fail",
            "run_id": "r-fail",
        },
        config={"configurable": {"thread_id": "t-fail"}},
    )
    assert s.get("dryrun_result", {}).get("success") is False
    assert s.get("human_review_status") == "approve"
    assert s.get("last_success_node") == "write_db"


# API 端到端测试依赖 ag_ui_langgraph 的 SSE 端点，后续可补充专用用例