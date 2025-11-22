## 目标

提供“无需 FastAPI，仅本地运行 Agent 图”的最小可复现实例，并逐步验证关键输出字段是否正确。

## 前置条件

* 已安装依赖：`pip install -r backend/requirements.txt`

* 确认 Python 版本 `>=3.10`

## 本地直接运行示例（一）Inline Python 调用

在项目根目录执行：

```bash
python - <<'PY'
from backend.graph.graph import graph

# 1) 准备输入（用户规格与因子名）
inputs = {
  "user_spec": "收盘价动量因子",
  "factor_name": "CloseMomentum"
}

# 2) 调用 Agent 图
res = graph.invoke(inputs)

# 3) 打印关键校验点
print({
  "factor_name": res.get("factor_name"),
  "has_code": bool(res.get("factor_code")),
  "dryrun": res.get("dryrun_result"),
  "semantic": res.get("semantic_check"),
  "human": res.get("human_review_status"),
  "eval": res.get("eval_metrics"),
  "db": res.get("db_write_status"),
})
PY
```

期望输出包含：

* `has_code: True`（代码已按模板生成）

* `dryrun: {"ok": True, ...}`（试运行占位成功）

* `semantic: {"ok": True}`（语义对齐占位通过）

* `human: "approved"`（HITL 占位通过）

* `eval`（mock 指标字典）与 `db: "success"`（mock 入库成功）

## 本地直接运行示例（二）单行命令

无需多行脚本，快速检查编排可用性：

```bash
python -c "from backend.graph.graph import graph; print(graph.invoke({'user_spec':'收盘价动量因子','factor_name':'CloseMomentum'}))"
```

观察返回字典是否包含 `factor_code/dryrun_result/semantic_check/human_review_status/eval_metrics/db_write_status` 等关键字段。

## 验证要点

* 图编排路径（收集→生成→dryrun→语义→HITL→回填评价→入库）是否走通

* 模板生成的 `factor_code` 是否非空

* `dryrun_result.ok` 是否为 True

* `eval_metrics` 是否包含各项指标占位

* `db_write_status` 是否为 `success`

## 可选后续增强（不在本次执行范围内）

* 增加“语义失败→ReAct 重试”演示：为 `semantic_check` 节点引入可控开关或根据输入触发失败，再观察 `retries_left` 递减与回到 `gen_code_react`。

* 将 `gen_code_react` 升级为 `create_react_agent` 的真实 ReAct 代理，结合 dryrun/语义差异进行迭代修复。

## 注意事项

* 若导入失败，请确认依赖已安装（尤其是 `langgraph`、`pydantic`）。

* 本示例仅运行“Agent 图本身”，不依赖 FastAPI，也不访问 `/agent` SSE

