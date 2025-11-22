from fastapi import FastAPI
import uuid

try:
    from ag_ui_langgraph import add_langgraph_fastapi_endpoint  # type: ignore
except Exception:
    add_langgraph_fastapi_endpoint = None

from .graph.graph import graph


app = FastAPI()

if add_langgraph_fastapi_endpoint is not None:
    add_langgraph_fastapi_endpoint(app, graph, "/agent")


@app.post("/agent/run")
async def run_agent(payload: dict):
    thread_id = payload.get("thread_id") or str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    init_state = {
        "user_spec": payload.get("user_spec", ""),
        "factor_name": payload.get("factor_name", "factor"),
        "retries_left": 5,
        "thread_id": thread_id,
        "run_id": run_id,
    }
    result = graph.invoke(init_state, config={"configurable": {"thread_id": thread_id}})
    return {"state": result}