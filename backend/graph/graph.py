import sys
import os
module_path = os.path.join(os.path.dirname(__file__), "../..")
print(module_path)
sys.path.append(module_path)
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from backend.graph.state import FactorAgentState
from backend.graph import nodes


def build_graph() -> StateGraph:
    """构建工作流图

    - 入口：`collect_spec`
    - 纯 Command 路由：各节点内返回下一跳
    - 终点：`finish -> END`
    """
    g = StateGraph(FactorAgentState)
    g.add_node("collect_spec", nodes.collect_spec)
    g.add_node("gen_code_react", nodes.gen_code_react)
    g.add_node("dryrun", nodes.dryrun)
    g.add_node("semantic_check", nodes.semantic_check)
    # 兼容层节点（保留但不使用）：react_retry_update / error_resume_router
    g.add_node("react_retry_update", nodes.react_retry_update)
    g.add_node("error_resume_router", nodes.error_resume_router)
    g.add_node("human_review_gate", nodes.human_review_gate)
    g.add_node("backfill_and_eval", nodes.backfill_and_eval)
    g.add_node("write_db", nodes.write_db)
    g.add_node("finish", nodes.finish)

    g.set_entry_point("collect_spec")
    # 纯 Command 模式：由节点返回的 Command 控制路由，不声明中间边

    # 终点边：finish → END
    g.add_edge("finish", END)
    # 保留：finish 边已声明

    return g

graph = build_graph().compile(checkpointer=MemorySaver())
# 打印langgraph的流程图
graph_image = graph.get_graph().draw_mermaid_png()
with open("workflow.png", "wb") as f:
    f.write(graph_image)
print("流程图已保存为 workflow.png")
"""图编排定义（纯 Command 路由）

本模块构建 LangGraph 工作流。节点自身用 `Command(goto=..., update=...)` 控制路由，
因此在图层只保留必要的入口与终点边，避免多节点并发写同一键导致的通道冲突。
兼容层节点（如 `error_resume_router`、`react_retry_update`）被保留但不参与路由。
"""

