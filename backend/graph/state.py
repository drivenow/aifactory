from typing import TypedDict, Optional, Dict, List


class FactorAgentState(TypedDict, total=False):
    """Agent 运行时状态字典（轻量版本，便于与 LangGraph/AG-UI 交互）"""
    messages: List[Dict]  # 对话/轨迹消息滑窗
    user_spec: str  # 因子自然语言描述
    factor_name: Optional[str]  # 因子名称
    factor_code: Optional[str]  # 模板化生成的因子代码
    retries_left: int  # 兼容旧字段：剩余自动重试次数
    dryrun_result: Optional[Dict]  # 试运行结果：{success, traceback}
    semantic_check: Optional[Dict]  # 语义一致性：{pass, diffs, reason}
    human_review_status: str  # 人审状态：pending/edited/approved/rejected
    human_edits: Optional[str]  # 人工修改后的代码或补丁
    eval_metrics: Optional[Dict]  # 因子评价指标（mock/真实）
    backfill_job_id: Optional[str]  # 历史回填任务 ID
    db_write_status: Optional[str]  # 入库状态
    thread_id: Optional[str]  # 线程 ID（用于 MemorySaver 检查点）
    run_id: Optional[str]  # 本次调用 ID
    last_success_node: Optional[str]  # 最近一次成功节点名
    error: Optional[str]  # 最近错误信息
    route: Optional[str]  # 当前路由（用于前端显示进度）
    should_interrupt: Optional[bool]  # 是否进入 HITL 中断
    retry_count: Optional[int]  # 已重试次数（用于强制中断）
    system_date: Optional[str]  # 系统日期（可用于提示词/审计）
    overwrite_fields: Optional[List[str]]  # 需要覆盖/置空的字段列表
    short_summary: Optional[str]  # 对话短摘要（跨阶段上下文稳定）
    artifacts: Optional[Dict]  # 工件集合：代码/日志/报告等
"""后端状态模型定义（LangGraph ↔ AG-UI）

该模块定义了因子编码助手在运行过程中的共享状态。状态通过 LangGraph 在各节点之间传递，
同时也会通过 AG-UI 协议映射到前端（CopilotKit）以便展示轨迹、进行 HITL 人审等交互。
"""