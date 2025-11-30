import pytest
from fastapi.testclient import TestClient
from backend.app import app
import json as _json
import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

def make_min_payload(
    thread_id: str = "t-demo-001",
    run_id: str = "r-demo-001",
    content: str = "5日滚动均值因子",
    msg_id: str = "msg-001",
    user_id: str = "u-demo-001",
    state: Optional[dict] = None,
):
    payload = {
        "threadId": thread_id,
        "runId": run_id,
        "messages": [
            {
                "id": msg_id,
                "role": "user",
                "content": content,
                "user": {"id": user_id},
            }
        ],
        "tools": [],
        "context": [],
        "forwardedProps": {},
        "state": state or {
            "user_spec": content,
            "factor_name": "MA5",
            "retry_count": 0,
        },
    }
    return payload

def collect_data_frames(r, max_lines: int = 400) -> List[Dict[str, Any]]:
    frames: List[Dict[str, Any]] = []
    for i, chunk in enumerate(r.iter_lines()):
        if i >= max_lines:
            break
        if not chunk:
            continue
        line = chunk.decode("utf-8") if isinstance(chunk, (bytes, bytearray)) else str(chunk)
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        try:
            obj = _json.loads(payload)
            frames.append(obj)
        except Exception:
            frames.append({"_raw": payload})
    return frames

TIME_KEYS = ("timestamp", "created_at", "time", "ts", "date", "datetime")

def extract_time_value(obj: Dict[str, Any]) -> Optional[Tuple[str, Any]]:
    for k in TIME_KEYS:
        if k in obj:
            return (k, obj[k])
    ev = obj.get("event")
    if isinstance(ev, dict):
        for k in TIME_KEYS:
            if k in ev:
                return (k, ev[k])
        meta = ev.get("metadata")
        if isinstance(meta, dict):
            for k in TIME_KEYS:
                if k in meta:
                    return (k, meta[k])
        data = ev.get("data")
        if isinstance(data, dict):
            for k in TIME_KEYS:
                if k in data:
                    return (k, data[k])
            for subk in ("output", "input"):
                sub = data.get(subk)
                if isinstance(sub, dict):
                    for k in TIME_KEYS:
                        if k in sub:
                            return (k, sub[k])
    return None

def normalize_time(val: Any) -> float:
    if isinstance(val, (int, float)):
        if val > 1e12:
            return float(val) / 1000.0
        return float(val)
    if isinstance(val, str):
        v = val.replace("Z", "+00:00")
        return dt.datetime.fromisoformat(v).timestamp()
    raise AssertionError(f"不支持的时间类型: {type(val)} {val}")

def test_sse_endpoint_connects_and_streams():
    client = TestClient(app)
    payload = make_min_payload()
    with client.stream(
        "POST",
        "/agent",
        json=payload,
        headers={"accept": "text/event-stream"},
    ) as r:
        assert r.status_code == 200
        assert "text/event-stream" in (r.headers.get("content-type") or "")
        frames = collect_data_frames(r, max_lines=50)
        assert len(frames) > 0

def test_sse_stream_contains_valid_time_and_monotonic():
    client = TestClient(app)
    payload = make_min_payload()
    with client.stream(
        "POST",
        "/agent",
        json=payload,
        headers={"accept": "text/event-stream"},
    ) as r:
        frames = collect_data_frames(r, max_lines=400)
        assert frames
    times: List[float] = []
    for f in frames:
        if not isinstance(f, dict):
            continue
        found = extract_time_value(f)
        if not found:
            continue
        _, raw_t = found
        tsec = normalize_time(raw_t)
        times.append(tsec)
    if len(times) == 0:
        steps: List[int] = []
        for f in frames:
            if not isinstance(f, dict):
                continue
            ev = f.get("event")
            if isinstance(ev, dict):
                meta = ev.get("metadata")
                if isinstance(meta, dict):
                    ls = meta.get("langgraph_step")
                    if isinstance(ls, int):
                        steps.append(ls)
                tags = ev.get("tags")
                if isinstance(tags, list):
                    for t in tags:
                        if isinstance(t, str) and t.startswith("graph:step:"):
                            try:
                                steps.append(int(t.split(":")[-1]))
                            except Exception:
                                pass
        assert len(steps) > 0, f"未找到时间字段或步骤字段。前 3 帧示例: {frames[:3]}"
        for i in range(1, len(steps)):
            assert steps[i] >= steps[i - 1], f"步骤倒退: {steps[i-1]} -> {steps[i]} 对应帧: {frames[max(0,i-2):i+1]}"
        return
    for i in range(1, len(times)):
        assert times[i] >= times[i - 1], f"事件时间倒退: {times[i-1]} -> {times[i]} 对应帧: {frames[max(0,i-2):i+1]}"

def test_raw_event_shape_is_supported():
    client = TestClient(app)
    payload = make_min_payload()
    with client.stream(
        "POST",
        "/agent",
        json=payload,
        headers={"accept": "text/event-stream"},
    ) as r:
        frames = collect_data_frames(r, max_lines=200)
    has_raw = any(isinstance(f, dict) and f.get("type") == "RAW" and isinstance(f.get("event"), dict) for f in frames)
    assert has_raw, f"未检测到 RAW 事件形态，帧示例: {frames[:3]}"