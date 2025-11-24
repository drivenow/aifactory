def human_review_gate(state: FactorAgentState) -> Command:
    """
    LangGraph 1.0 风格的 HITL 节点（使用 interrupt）

    - 第一次运行到这里：
        * 构造 req（人审请求 payload）
        * 调用 interrupt(req) → 图暂停，req 通过 AG-UI 事件流返回给前端
    - 前端调用 resolve(...) 回复后：
        * 再次运行到这里，interrupt(req) 返回 ui_resp
    """
    req = {
        "type": "code_review",
        "title": "Review generated factor code",
        "code": state.get("factor_code", "") or "",
        "actions": ["approve", "edit", "reject"],
        "retry_count": int(state.get("retry_count", 0)),
    }

    ui_resp = interrupt(req)

    # 调试看看原始返回
    print(
        f"[DBG] human_review_gate resume thread={state.get('thread_id')} "
        f"resp_raw={ui_resp!r} type={type(ui_resp)}"
    )

    # 1) 字符串 → 尝试当 JSON 解析
    if isinstance(ui_resp, str):
        try:
            ui_resp = json.loads(ui_resp)
        except Exception:
            ui_resp = {"status": ui_resp}

    # 2) 再兜底一次：必须是 dict
    if not isinstance(ui_resp, dict):
        ui_resp = {"status": str(ui_resp)}

    # 3) 把“嵌套的 status”解开：
    status_raw = ui_resp.get("status") or ui_resp.get("human_review_status")
    if isinstance(status_raw, dict):
        status = status_raw.get("status") or status_raw.get("human_review_status")
    else:
        status = status_raw

    edited_code = ui_resp.get("edited_code") or ui_resp.get("factor_code")

    # 记录事件
    events = _push_event(
        state,
        {
            "type": "hitl_decision",
            "node": "human_review_gate",
            "status": status,
        },
    )

    # --- 审核通过 / 编辑后通过 → 进入回填+评价 ---
    if status in ("approved", "edited"):
        final_code = edited_code or state.get("factor_code")
        return Command(
            goto="backfill_and_eval",
            update={
                "ui_request": req,
                "ui_response": ui_resp,
                "human_review_status": status,
                "human_edits": edited_code,
                "factor_code": final_code,
                "last_success_node": "human_review_gate",
                "error": None,
                "route": "backfill_and_eval",
                "events": events,
            },
        )

    # --- 审核直接拒绝 → 直接结束 ---
    if status == "rejected":
        return Command(
            goto="finish",
            update={
                "ui_request": req,
                "ui_response": ui_resp,
                "human_review_status": "rejected",
                "last_success_node": "human_review_gate",
                "error": None,
                "route": "finish",
                "events": events,
            },
        )

    # --- 兜底：status 异常，也当 reject 处理 ---
    return Command(
        goto="finish",
        update={
            "ui_request": req,
            "ui_response": ui_resp,
            "human_review_status": "rejected",
            "last_success_node": "human_review_gate",
            "error": {
                "node": "human_review_gate",
                "message": f"invalid ui_response status={status!r}",
            },
            "route": "finish",
            "events": events,
        },
    )
