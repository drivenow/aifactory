# backend/graph/state.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import TypedDict, Optional, Dict, List, Any, Callable
from typing_extensions import Annotated, Literal
from functools import wraps
# from langgraph.graph.message import add_messages
import traceback

# =========================
# 类型定义
# =========================

# 路由枚举（与 graph 中的节点名保持一致）
Route = Literal[
    "collect_spec_from_messages",
    "gen_code_react",
    "dryrun",
    "semantic_check",
    "human_review_gate",
    "backfill_and_eval",
    "write_db",
    "finish",
]

HumanReviewStatus = Literal[
    "pending",
    "review",   # ✅ 新增：只给审核意见
    "edit",
    "approve",
    "rejecte",
]

DBWriteStatus = Literal["pending", "success", "failed"]


def wrap_state_error(
    where: str,
    state_arg: str = "state",
    thread_id_key: str = "thread_id",
    dbg_prefix: str = "[DBG_VIEW]",
):
    """
    where: 报错来源标识，比如 "LogicView.from_state"
    state_arg: 被装饰函数里 state 的参数名（默认 "state"）
    thread_id_key: 从 state 里取 thread_id 的 key
    """
    def deco(fn: Callable[..., Any]):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # 取 state（支持位置参数或关键字参数）
            state = kwargs.get(state_arg, None)
            if state is None:
                # 尝试从位置参数里猜（对 classmethod: args=(cls, state, ...)）
                for a in args:
                    if isinstance(a, dict) and state_arg not in kwargs:
                        state = a
                        break

            try:
                return fn(*args, **kwargs)
            except Exception as e:
                print(f"{dbg_prefix} {where} {state_arg}={state}")
                traceback.print_exc()

                thread_id = None
                if isinstance(state, dict):
                    thread_id = state.get(thread_id_key)

                raise Exception(
                    f"{where} error thread={thread_id} msg={str(e)}"
                ) from e
        return wrapper
    return deco

class ViewBase(BaseModel):
    @classmethod
    def _wrap_from_state(cls, where=None):
        return wrap_state_error(where or f"{cls.__name__}.from_state")

# -------------------------
# 顶层 State：组合所有子 State
# -------------------------

def add_errors(left, right):
    left = left or []
    if right is None:
        return left
    if isinstance(right, list):
        return left + right
    return left + [right]

def keep_last(left, right):
    return right if right is not None else left

class FactorAgentState(
    TypedDict,
    total=False,
):
    """
    Agent 运行时状态字典（轻量版本，便于与 LangGraph/AG-UI 交互）

    注意：
    - 这是多个子 State 的组合，不额外新增字段，只是把语义拆得更清晰。
    - 现有节点与前端中使用的字段名保持不变。
    """

    """RetryState 重试控制与错误信息"""

    retry_count: Optional[int]          # 已重试次数（用于强制 HITL）
    error: Annotated[List[str], add_errors] #把 error 改成可聚合通道， langgraph会合并状态
    last_success_node: Annotated[str, keep_last]    # 最近一次成功节点名, langgraph会合并状态
    route: Annotated[Route, keep_last]              # 当前路由（用于前端显示进度）

    """ConversationState 对话/轨迹相关的元信息（由 LangGraph / CopilotKit 自动注入）"""

    messages: List[Any]      # 对话/轨迹消息滑窗
    short_summary: Optional[str]        # 对话短摘要（跨阶段上下文稳定）
    system_date: Optional[str]          # 系统日期（可用于提示词/审计）
    run_id: Optional[str]               # 本次调用 ID
    thread_id: Optional[str]            # 线程 ID（MemorySaver checkpoint 使用）

    """LogicState 用户意图 / 因子描述"""

    user_spec: str                      # 因子自然语言描述
    factor_name: Optional[str]          # 因子名称/标识
    code_mode: Optional[str]            # 代码生成模式：pandas / l3_py

    """CodeGenState 代码生成阶段产物"""

    factor_code: Annotated[str, keep_last]          # 生成的因子代码（模板化）
    dryrun_result: Optional[Dict[str, Any]]   # 试运行结果：{success, stdout, stderr, traceback}
    semantic_check: Optional[Dict[str, Any]]  # 语义一致性：{pass, diffs, reason}

    """HumanReviewState 人审相关状态（HITL）"""

    ui_request: Optional[Dict[str, Any]]      # 后端发起的人审请求 payload
    ui_response: Optional[Dict[str, Any]]     # 前端回传的人审结果 payload
    human_review_status: Optional[HumanReviewStatus] = "pending"    # 人审状态：pending/edit/approve/rejecte
    review_comment: Optional[str] = None      # 人工审核的评论
    human_edits: Optional[str]                # 人工修改后的代码
    should_interrupt: bool = True   # 是否进入 HITL 中断（诊断/前端显示）


    """EvalState 回填 / 评估 / 入库"""
    backfill_job_id: Optional[str]            # 历史回填任务 ID
    eval_metrics: Optional[Dict[str, Any]]    # 因子评价指标（mock/真实）
    db_write_status: Optional[DBWriteStatus]  # 入库状态：success/failed/unknown


class FactorAgentStateModel(BaseModel):
    """
    Pydantic 版的 FactorAgentState，用于强校验/文档。

    注意：
    - 字段尽量和 TypedDict 版本字段名保持一致（扁平结构）
    - 这里给了一些合理的默认值，方便在部分缺失字段时也能正常工作

    使用方法：
    在某个你非常在意正确性的节点里（例如 backfill_and_eval），可以加一行
    # 做一次强校验，异常就直接抛，走统一重试/HITL 路径
    FactorAgentStateModel.from_state(state)
    """

    # ConversationState
    messages: List[Any] = Field(default_factory=list)
    short_summary: Optional[str] = None
    system_date: Optional[str] = None
    run_id: Optional[str] = None
    thread_id: Optional[str] = None

    # RetryState
    retry_count: int = 0
    error: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    last_success_node: Optional[str] = None
    route: Optional[Route] = None

    # LogicState
    user_spec: str = ""                      # 默认为空字符串
    factor_name: Optional[str] = "factor"    # 默认因子名
    code_mode: Optional[str] = "pandas"

    # CodeGenState
    factor_code: Optional[str] = None
    overwrite_fields: List[str] = Field(default_factory=list)

    # ExecutionState
    dryrun_result: Dict[str, Any] = Field(default_factory=dict)
    semantic_check: Dict[str, Any] = Field(default_factory=dict)

    # HumanReviewState
    ui_request: Dict[str, Any] = Field(default_factory=dict)
    ui_response: Dict[str, Any] = Field(default_factory=dict)
    human_review_status: HumanReviewStatus = "pending"
    human_edits: Optional[str] = None
    review_comment: Optional[str] = None  # ✅ 新增
    should_interrupt: bool = True

    # EvalState
    backfill_job_id: Optional[str] = None
    eval_metrics: Dict[str, Any] = Field(default_factory=dict)
    db_write_status: Optional[DBWriteStatus] = "pending"

    class Config:
        # 如果你希望 state 里偶尔多塞调试字段，又不想报错，可以打开这一行
        # extra = "ignore"
        pass

    @classmethod
    def from_state(cls, state: "FactorAgentState") -> "FactorAgentStateModel":
        """
        从 TypedDict 版 FactorAgentState 构造一个强类型的 Model，
        用于节点内部的 debug/断言。
        """
        return cls(**dict(state))
