# backend/graph/graph.py
from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.graph.state import FactorAgentState
from backend.graph import nodes


def build_graph() -> StateGraph:
    """
    构建工作流图（纯 Command 路由 + HITL interrupt）

    入口：collect_spec
    路由：所有中间跳转由各节点返回 Command(goto=..., update=...) 控制
    终点：finish → END（显式加边，便于可视化与稳定性）

    约定：
    - 每个节点都返回 Command(goto=..., update=...)
    - human_review_gate 使用 interrupt(...) 触发 HITL 中断，LangGraph/AG-UI 会负责 resume
    - 图层只声明入口和 finish->END 的边，其他跳转都由 Command 决定
    """
    g = StateGraph(FactorAgentState)

    # 主流程节点
    g.add_node("collect_spec", nodes.collect_spec)
    g.add_node("gen_code_react", nodes.gen_code_react)
    g.add_node("dryrun", nodes.dryrun)
    g.add_node("semantic_check", nodes.semantic_check)
    g.add_node("human_review_gate", nodes.human_review_gate)
    g.add_node("backfill_and_eval", nodes.backfill_and_eval)
    g.add_node("write_db", nodes.write_db)
    g.add_node("finish", nodes.finish)

    # 入口
    g.set_entry_point("collect_spec")

    # 纯 Command 模式：不声明中间边
    # 但显式声明 finish -> END，避免未来改动时产生悬空终点
    g.add_edge("finish", END)

    return g


# compile 一个可复用的 graph 实例（HTTP / CLI 共用）
graph = build_graph().compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    # 手动运行本文件时生成流程图，避免 import 副作用
    try:
        graph_image = graph.get_graph().draw_mermaid_png()
        with open("workflow.png", "wb") as f:
            f.write(graph_image)
        print("流程图已保存为 workflow.png")
    except Exception as e:
        print("[WARN] draw graph failed:", e)



if __name__ == "__main__":
    # 仅在手动运行本文件时生成流程图，避免 import 副作用
    try:
        graph_image = graph.get_graph().draw_mermaid_png()
        with open("workflow.png", "wb") as f:
            f.write(graph_image)
        print("流程图已保存为 workflow.png")
    except Exception as e:
        print("[WARN] draw graph failed:", e)



