# graph.py
from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.graph.state import FactorAgentState
from backend.graph import nodes


def build_graph() -> StateGraph:
    """构建工作流图（纯 Command 路由 + HITL interrupt）

    入口：collect_spec
    路由：所有中间跳转由各节点返回 Command(goto=..., update=...) 控制
    终点：finish → END（显式加边，便于可视化与稳定性）

    新版 nodes.py 里每一步都会明确返回：
    正常流：Command(goto="dryrun"/"semantic_check"/"human_review_gate"/...)
    重试流：_route_retry_or_hitl(...)
    HITL 发起：Command(goto="__interrupt__")
    HITL 恢复后继续：依然返回 Command(goto=...)
    所以图层不需要声明 collect_spec -> gen_code_react 之类的边。

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
    # 但建议显式声明 finish -> END，避免未来改动时产生悬空终点
    g.add_edge("finish", END)

    return g


# compile 一个可复用的 graph 实例
graph = build_graph().compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    # 仅在手动运行本文件时生成流程图，避免 import 副作用
    try:
        graph_image = graph.get_graph().draw_mermaid_png()
        with open("workflow.png", "wb") as f:
            f.write(graph_image)
        print("流程图已保存为 workflow.png")
    except Exception as e:
        print("[WARN] draw graph failed:", e)


"""
图编排定义（纯 Command 路由 + 方案 A）

本模块构建 LangGraph 工作流。节点自身用 Command(goto=..., update=...) 控制路由，
并在 human_review_gate 中使用 goto="__interrupt__" 发起 AG-UI ui_request，
等待前端 ui_response 后自动 resume。

图层仅保留必须的入口与 finish->END 终点边，避免多节点并发写同一键导致冲突。
"""
