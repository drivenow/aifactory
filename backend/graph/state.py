from typing import TypedDict, Optional, Dict, List


class FactorAgentState(TypedDict, total=False):
    messages: List[Dict]
    user_spec: str
    factor_name: Optional[str]
    factor_code: Optional[str]
    retries_left: int
    dryrun_result: Optional[Dict]
    semantic_check: Optional[Dict]
    human_review_status: str
    human_edits: Optional[str]
    eval_metrics: Optional[Dict]
    backfill_job_id: Optional[str]
    db_write_status: Optional[str]
    thread_id: Optional[str]
    run_id: Optional[str]
    last_success_node: Optional[str]