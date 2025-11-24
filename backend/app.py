import sys
sys.path.append("/Users/fullmetal/Documents/agent_demo/")
import os
from backend.graph.graph import graph
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ag_ui_langgraph import add_langgraph_fastapi_endpoint, LangGraphAgent as BaseLangGraphAgent
import os
import uvicorn

app = FastAPI(title="langgraph demo with agui")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or ["http://localhost:3000"] for security
    allow_credentials=False,  # Add this for cookies/SSE if needed
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 自己包一层，关闭 schema 过滤
class FullStateLangGraphAgent(BaseLangGraphAgent):
    def get_state_snapshot(self, state):
        # 直接把 LangGraph 的 state 原样透给前端，不做字段过滤
        return state

agent = FullStateLangGraphAgent(name="factor_agent", graph=graph)
add_langgraph_fastapi_endpoint(app, agent, "/agent")

@app.middleware("http")
async def log_requests(request, call_next):
    try:
        print("[DBG] request", request.method, request.url.path)
    except Exception:
        pass
    response = await call_next(request)
    try:
        print("[DBG] response", request.url.path, response.status_code)
    except Exception:
        pass
    return response

# 使用默认 AG-UI 端点：/agent（POST，SSE）与 /agent/health（GET）
def main():
    """启动 uvicorn 服务（开发模式）"""
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("backend.app:app", host="0.0.0.0", port=port, reload=True)


"""
add_langgraph_fastapi_endpoint(app, graph, "/agent") 会自动生成 AG-UI 兼容的路由，至少包括：
(1)运行 graph 并返回 SSE 事件流
- POST /agent
- Accept: text/event-stream 时会以 SSE 连续吐事件

(2) 健康检查
- GET /agent/health
- Human-in-loop 回传接口 路径通常是 /agent/human-feedback 或 /agent/feedback

(3)确认 human-feedback 的准确路径
启动服务后打开：
http://localhost:8000/docs
"""

if __name__=="__main__":
    main()
"""FastAPI 入口（AG-UI + LangGraph SSE）

该模块将工作流图包装为 AG-UI 兼容的 SSE 服务端点，供 CopilotKit 前端消费。
核心：`/agent` POST（SSE流）与 `/agent/health` 健康检查。
"""
