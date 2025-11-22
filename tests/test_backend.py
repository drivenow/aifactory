import json

from backend.graph.graph import graph
from backend.app import app

def test_graph_success_flow():
    s = graph.invoke(
        {
            "user_spec": "5日滚动均值因子",
            "factor_name": "MA5",
            "retries_left": 5,
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
            "retries_left": 1,
            "thread_id": "t-fail",
            "run_id": "r-fail",
        },
        config={"configurable": {"thread_id": "t-fail"}},
    )
    assert s.get("dryrun_result", {}).get("success") is False
    assert s.get("human_review_status") == "approved"
    assert s.get("last_success_node") == "write_db"


def test_api_success_flow():
    from fastapi.testclient import TestClient

    client = TestClient(app)
    resp = client.post(
        "/agent/run",
        json={
            "user_spec": "5日滚动均值因子",
            "factor_name": "MA5",
            "thread_id": "t-api",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    state = body.get("state", {})
    assert state.get("db_write_status") == "success"
    assert state.get("last_success_node") == "write_db"