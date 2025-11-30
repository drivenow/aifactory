# backend/graph/state.py
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


# -------------------------
# 子 State：功能维度拆分
# -------------------------

class ConversationState(TypedDict, total=False):
    """对话/轨迹相关的元信息（由 LangGraph / CopilotKit 自动注入）"""

    messages: List[Dict[str, Any]]      # 对话/轨迹消息滑窗
    short_summary: Optional[str]        # 对话短摘要（跨阶段上下文稳定）
    system_date: Optional[str]          # 系统日期（可用于提示词/审计）
    run_id: Optional[str]               # 本次调用 ID
    thread_id: Optional[str]            # 线程 ID（MemorySaver checkpoint 使用）


class LogicState(TypedDict, total=False):
    """用户意图 / 因子描述"""

    user_spec: str                      # 因子自然语言描述
    factor_name: Optional[str]          # 因子名称/标识


class CodeGenState(TypedDict, total=False):
    """代码生成阶段产物"""

    factor_code: Optional[str]          # 生成的因子代码（模板化）
    artifacts: Optional[Dict[str, Any]] # 工件集合：代码/日志/报告等
    overwrite_fields: Optional[List[str]]  # 需要覆盖/置空的字段列表


class RetryState(TypedDict, total=False):
    """重试控制与错误信息"""

    retry_count: Optional[int]          # 已重试次数（用于强制 HITL）
    error: Optional[Dict[str, Any]]     # 最近错误信息（{node,message,traceback?}）
    last_success_node: Optional[str]    # 最近一次成功节点名


class ExecutionState(TypedDict, total=False):
    """执行阶段的一些中间结果"""

    dryrun_result: Optional[Dict[str, Any]]   # 试运行结果：{success, stdout, stderr, traceback}
    semantic_check: Optional[Dict[str, Any]]  # 语义一致性：{pass, diffs, reason}


class HumanReviewState(TypedDict, total=False):
    """人审相关状态（HITL）"""

    ui_request: Optional[Dict[str, Any]]      # 后端发起的人审请求 payload
    ui_response: Optional[Dict[str, Any]]     # 前端回传的人审结果 payload
    human_review_status: HumanReviewStatus    # 人审状态：pending/edited/approved/rejected
    human_edits: Optional[str]                # 人工修改后的代码
    should_interrupt: bool = True   # 是否进入 HITL 中断（诊断/前端显示）


class EvalState(TypedDict, total=False):
    """回填 / 评估 / 入库"""

    backfill_job_id: Optional[str]            # 历史回填任务 ID
    eval_metrics: Optional[Dict[str, Any]]    # 因子评价指标（mock/真实）
    db_write_status: Optional[DBWriteStatus]  # 入库状态：success/failed/unknown


class ProgressState(TypedDict, total=False):
    """整体工作流进度"""

    route: Optional[Route]                    # 当前路由（用于前端显示进度）


# -------------------------
# 顶层 State：组合所有子 State
# -------------------------

class FactorAgentState(
    ConversationState,
    LogicState,
    CodeGenState,
    RetryState,
    ExecutionState,
    HumanReviewState,
    EvalState,
    ProgressState,
    total=False,
):
    """
    Agent 运行时状态字典（轻量版本，便于与 LangGraph/AG-UI 交互）

    注意：
    - 这是多个子 State 的组合，不额外新增字段，只是把语义拆得更清晰。
    - 现有节点与前端中使用的字段名保持不变。
    """

    # 不额外添加字段；所有字段均来自各子 State 的组合
    pass
