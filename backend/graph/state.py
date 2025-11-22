from typing import TypedDict, Optional, Dict, List


class FactorAgentState(TypedDict, total=False):
    """Agent 运行时状态（LangGraph ↔ AG-UI 可共享）

    在后端图节点与前端事件之间传递因子生成/试运行/人审/评价/入库等数据。
    """
    messages: List[Dict]  # 消息列表：前后端共享对话/轨迹
    user_spec: str  # 必传：用户因子描述（自然语言），如果没传，会从message中获取
    factor_name: Optional[str]  # 因子名称标识
    factor_code: Optional[str]  # 生成的因子 Python 代码（模板化）
    retries_left: int  # 剩余自动重试次数（ReAct）
    dryrun_result: Optional[Dict]  # 试运行结果/错误信息
    semantic_check: Optional[Dict]  # 语义一致性检查结果
    human_review_status: str  # 人审状态：pending/edited/approved/rejected
    human_edits: Optional[str]  # 人审修改内容（代码 diff 或文本）
    eval_metrics: Optional[Dict]  # 因子评价指标（mock/真实）
    backfill_job_id: Optional[str]  # 历史回填任务 ID
    db_write_status: Optional[str]  # 入库状态
    thread_id: Optional[str]  # 线程 ID（只读展示），用于检查点记忆隔离
    run_id: Optional[str]  # 本次调用 ID（只读展示）
    last_success_node: Optional[str]  # 上次成功的节点名（用于错误回退定位）
    error: Optional[str]  # 最近一次错误信息（用于错误回退定位）