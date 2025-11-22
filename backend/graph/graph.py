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
    g = StateGraph(FactorAgentState)
    g.add_node("collect_spec", nodes.collect_spec)
    g.add_node("gen_code_react", nodes.gen_code_react)
    g.add_node("dryrun", nodes.dryrun)
    g.add_node("semantic_check", nodes.semantic_check)
    g.add_node("react_retry_update", nodes.react_retry_update)
    g.add_node("error_resume_router", nodes.error_resume_router)
    g.add_node("human_review_gate", nodes.human_review_gate)
    g.add_node("backfill_and_eval", nodes.backfill_and_eval)
    g.add_node("write_db", nodes.write_db)
    g.add_node("finish", nodes.finish)

    g.set_entry_point("collect_spec")
    g.add_edge("collect_spec", "gen_code_react")
    g.add_edge("gen_code_react", "dryrun")
    g.add_conditional_edges(
        "dryrun",
        nodes.error_resume_router,
        {
            "pass": "semantic_check",
            "resume_to_gen_code_react": "gen_code_react",
            "resume_to_dryrun": "dryrun",
            "resume_to_semantic_check": "semantic_check",
            "resume_to_human_review_gate": "human_review_gate",
            "resume_to_backfill": "backfill_and_eval",
            "resume_to_write_db": "write_db",
        },
    )

    g.add_conditional_edges(
        "semantic_check",
        nodes.react_retry_router,
        {
            "pass": "human_review_gate",
            "retry": "react_retry_update",
        },
    )

    g.add_edge("react_retry_update", "gen_code_react")

    g.add_conditional_edges(
        "human_review_gate",
        lambda s: s.get("human_review_status", "approved"),
        {
            "approved": "backfill_and_eval",
            "edited": "backfill_and_eval",
            "rejected": "finish",
        },
    )

    g.add_edge("backfill_and_eval", "write_db")
    g.add_edge("write_db", "finish")
    g.add_edge("finish", END)

    return g

graph = build_graph().compile(checkpointer=MemorySaver())
# 打印langgraph的流程图
graph_image = graph.get_graph().draw_mermaid_png()
with open("workflow.png", "wb") as f:
    f.write(graph_image)
print("流程图已保存为 workflow.png")

