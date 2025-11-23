# state.py
from __future__ import annotations

from typing import TypedDict, Optional, Dict, List, Any
from typing_extensions import Literal


# -------------------------
# Enum-like Literals
# -------------------------

HumanReviewStatus = Literal["pending", "edited", "approved", "rejected"]

DBWriteStatus = Literal["success", "failed", "unknown"]

# route 用于前端进度展示 + 节点间可视化
Route = Literal[
    "collect_spec",
    "gen_code_react",
    "dryrun",
    "semantic_check",
    "human_review_gate",
    "backfill_and_eval",
    "write_db",
    "finish",
]


class FactorAgentState(TypedDict, total=False):
    """Agent 运行时状态字典（轻量版本，便于与 LangGraph/AG-UI 交互）"""

    # ---- conversation / trace ----
    messages: List[Dict[str, Any]]     # 对话/轨迹消息滑窗（CopilotKit/LangGraph 自动注入）
    short_summary: Optional[str]       # 对话短摘要（跨阶段上下文稳定）
    system_date: Optional[str]         # 系统日期（可用于提示词/审计）
    run_id: Optional[str]              # 本次调用 ID
    thread_id: Optional[str]           # 线程 ID（用于 MemorySaver checkpoint）

    # ---- user intent / spec ----
    user_spec: str                     # 因子自然语言描述
    factor_name: Optional[str]         # 因子名称/标识

    # ---- generation artifacts ----
    factor_code: Optional[str]         # 生成的因子代码（模板化）
    artifacts: Optional[Dict[str, Any]]# 工件集合：代码/日志/报告等
    overwrite_fields: Optional[List[str]]  # 需要覆盖/置空的字段列表

    # ---- auto-retry control ----
    retry_count: Optional[int]         # 已重试次数（用于强制 HITL）
    error: Optional[Dict[str, Any]]    # 最近错误信息（建议结构化：{node,message,traceback?}）
    last_success_node: Optional[str]   # 最近一次成功节点名

    # ---- dryrun & semantic check ----
    dryrun_result: Optional[Dict[str, Any]]     # 试运行结果：{success, stdout, stderr, traceback}
    semantic_check: Optional[Dict[str, Any]]    # 语义一致性：{pass, diffs, reason}

    # ---- HITL (方案 A: AG-UI) ----
    ui_request: Optional[Dict[str, Any]]        # AG-UI ui_request payload（后端发起人审）
    ui_response: Optional[Dict[str, Any]]       # AG-UI ui_response payload（前端回传人审）
    should_interrupt: Optional[bool]            # 是否进入 HITL 中断（诊断/前端显示）
    human_review_status: HumanReviewStatus      # 人审状态：pending/edited/approved/rejected
    human_edits: Optional[str]                  # 人工修改后的代码

    # ---- backfill / eval / persist ----
    backfill_job_id: Optional[str]              # 历史回填任务 ID
    eval_metrics: Optional[Dict[str, Any]]      # 因子评价指标（mock/真实）
    db_write_status: Optional[DBWriteStatus]    # 入库状态：success/failed/unknown

    # ---- progress ----
    route: Optional[Route]                      # 当前路由（用于前端显示进度）
