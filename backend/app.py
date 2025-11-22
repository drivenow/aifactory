from fastapi import FastAPI

from ag_ui_langgraph import add_langgraph_fastapi_endpoint  # type: ignore
from .graph.graph import graph


app = FastAPI()

add_langgraph_fastapi_endpoint(app, graph, "/agent")


@app.post("/agent/run")
async def run_agent(payload: dict):
    init_state = {
        "user_spec": payload.get("user_spec", ""),
        "factor_name": payload.get("factor_name", "factor"),
        "retries_left": 5,
    }
    result = graph.invoke(init_state)
    return {"state": result}