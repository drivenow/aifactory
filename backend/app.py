# backend/app.py
"""
FastAPI 入口（AG-UI + LangGraph SSE）

- 暴露 /agent 端点，供 CopilotKit / AG-UI 前端消费。
- 使用 FullStateLangGraphAgent，将 LangGraph 的 state 全量透出给前端。
"""

import sys
import os

# TODO: 这行是你本地开发用的路径 hack，正式项目建议改为标准包导入。
sys.path.append("/Users/fullmetal/Documents/agent_demo/")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ag_ui_langgraph import (
    add_langgraph_fastapi_endpoint,
    LangGraphAgent as BaseLangGraphAgent,
)
import uvicorn

from backend.graph.graph import graph  # ✅ 统一从这里拿 Graph 实例


app = FastAPI(title="langgraph demo with agui")

# 简单的 CORS 配置，方便本地前端调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 正式环境建议收紧
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FullStateLangGraphAgent(BaseLangGraphAgent):
    """
    自定义 LangGraphAgent，将 state 原封不动透给前端，而不是做字段过滤。

    这样前端的 useCoAgent<FactorAgentState>() 可以直接看到完整的运行时状态。
    """

    def get_state_snapshot(self, state):
        return state


# 注册 agent（名字保持 "factor_agent"，与前端对齐）
agent = FullStateLangGraphAgent(name="factor_agent", graph=graph)
add_langgraph_fastapi_endpoint(app, agent, "/agent")


@app.middleware("http")
async def log_requests(request, call_next):
    """简单的请求日志中间件，方便调试"""
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

(3)查看接口详情，启动服务后打开：
http://localhost:8001/docs
"""
if __name__ == "__main__":
    main()
"""FastAPI 入口（AG-UI + LangGraph SSE）

该模块将工作流图包装为 AG-UI 兼容的 SSE 服务端点，供 CopilotKit 前端消费。
核心：`/agent` POST（SSE流）与 `/agent/health` 健康检查。
"""

