# backend/graph/graph.py
from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.graph.state import FactorAgentState
from backend.graph import nodes


def build_graph() -> StateGraph:
    """
    构建工作流图（纯 route 字段 + conditional edges 控流，HITL interrupt）

    入口：collect_spec_from_messages
    路由：所有中间跳转由各节点返回 route 字段控制
    终点：finish → END（显式加边，便于可视化与稳定性）

    约定：
    - 每个节点都返回更新后的 state dict，并写入 route
    - human_review_gate 使用 interrupt(...) 触发 HITL 中断，LangGraph/AG-UI 会负责 resume
    - 图层只声明入口和 finish->END 的边，其他跳转都由 conditional edges 决定
    """
    g = StateGraph(FactorAgentState)

    # 主流程节点
    g.add_node("collect_spec_from_messages", nodes.collect_spec_from_messages)
    g.add_node("gen_code_react", nodes.gen_code_react)
    g.add_node("dryrun", nodes.dryrun)
    g.add_node("semantic_check", nodes.semantic_check)
    g.add_node("human_review_gate", nodes.human_review_gate)
    g.add_node("backfill_and_eval", nodes.backfill_and_eval)
    g.add_node("write_db", nodes.write_db)
    g.add_node("finish", nodes.finish)

    """
    一个简单的选型口诀：
    - 流程是“图结构” → 静态边
    - 流程是“节点决策” → Command.goto
    - 需要跨图/多 agent/原子跳转 → Command.goto
    - 想要最强可读性和可视化 → 静态边
    - 避坑：要么让节点用 Command 控流（不加外部 edges），要么用 edges（节点别返回 goto）。
        因为 goto 不会覆盖静态边，两边都会执行，且执行顺序是：先静态边目标，再 goto 目标。这个行为目前文档里也在补充说明中。

    以下用静态边 （线性、无分支）：

    collect_spec_from_messages / backfill_and_eval / write_db / finish
    主干最好静态边，异常/重试用 Command 。
    gen_code_react / dryrun / semantic_check

    一个简单的选型口诀（本图采用 route+conditional edges）：
    - 主干：collect_spec_from_messages / backfill_and_eval / write_db / finish 使用静态边
    - 分支：gen_code_react / dryrun / semantic_check / human_review_gate 由 route 控制跳转
    """
    g.set_entry_point("collect_spec_from_messages")
    g.add_edge("collect_spec_from_messages", "gen_code_react")

    def route_from_state(state: dict):
        route = state.get("route")
        if route == "END":
            return END
        return route

    g.add_conditional_edges(
        "gen_code_react",
        route_from_state,
        ["dryrun", "gen_code_react", "human_review_gate"],
    )
    g.add_conditional_edges(
        "dryrun",
        route_from_state,
        ["semantic_check", "gen_code_react", "human_review_gate"],
    )
    g.add_conditional_edges(
        "semantic_check",
        route_from_state,
        ["human_review_gate", "gen_code_react"],
    )
    g.add_conditional_edges(
        "human_review_gate",
        route_from_state,
        ["backfill_and_eval","dryrun","gen_code_react","finish"],
    )

    g.add_edge("backfill_and_eval", "write_db")
    g.add_edge("write_db", "finish")
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

