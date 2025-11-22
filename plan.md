# 开发需求

你是一个专业的Agent研发助手，请帮我用langgraph构建一个量化研究领域选股因子编码助手的Agent，用到create_react_agent构建代理，用agenteval做评估，并且通过copilotkit做前端展示。我需要搭建一个原型，请帮我出一个mvp设计方案。把后端和前端的方案分开，设计控制流和human in loop等事件流。

因子编码助手要实现的功能如下：
（0）准备一个因子模版，包含加载数据和计算功能；准备一套因子评价的代码，这些工具函数先mock实现，后续再替换为实例的业务逻辑。
（1）根据用户的描述，按照因子模板生成代码。
（2）代码试运行，如果运行失败或者产生的逻辑和用户描述不符合，引入react机制重试至多5次；
（3）代码生成完引入人工审核机制；允许human in loop修改和确认代码；
（4）代码经审核通过后，大模型编排流程，完成因子历史数据计算和因子评价结果入库。
（5）用langgraph再编写Agent，并将langgraph的标准事件定义，可以考虑用ai-ui-langgraph这个框架可以用于快速把langgraph转换为fastapi服务，暴露成fastapi后端；
（6）前后端交互应该是基于ag-ui协议，这个协议下langgraph的状态和标准事件流都可以传递到前端，copilot对接langgraph的标准事件，并做前端展示。 


下面是**基于你“第6部分及之后开发细节扩展”的修订**、并对前面不合适处做了替换后的**最终完整方案（单一终稿）**。我把所有内容重新组织成一份自洽、无阶段冲突的 MVP 设计文档，你可以直接作为项目设计稿使用。

---

# 量化研究选股因子编码助手 Agent（LangGraph + ReAct + agentevals + CopilotKit）

## MVP 最终方案（终稿）

> 目标：用 LangGraph 构建“因子编码助手”原型。
> 特性：模板化因子生成 → 沙盒试跑 → ReAct 修复重试（≤5）→ 人工审核（HITL）→ 历史回填 + 因子评价（mock）→ 入库（mock）→ AG-UI 事件流前端可观测与可干预。
> 原则：不造轮子，优先复用 LangGraph、create_react_agent、agentevals、ag-ui-langgraph（ai-ui-langgraph）、CopilotKit、AG-UI 协议。

---

## 0. 技术栈与轮子复用

### 0.1 后端选型

* **LangGraph**：编排 Agent 工作流（状态机/图）。
* **`langgraph.prebuilt.create_react_agent`**：代码生成 + 工具调用 + 反思修复的 ReAct 代理。
* **agentevals / agent-evals**：离线评估 agent 轨迹与输出，接入 LangSmith。
* **ag-ui-langgraph（ai-ui-langgraph）**：把 LangGraph 标准事件 & State 自动转成 **AG-UI SSE FastAPI 服务**。
* **FastAPI**：承载 SSE、健康检查、工件下载/鉴权/落库接口。

### 0.2 前端选型

* **Next.js / React**：UI 主框架。
* **CopilotKit**：直接消费 AG-UI SSE 事件；支持生成式 UI 与 HITL 交互。
* **AG-UI Protocol**：前后端一致的标准事件/状态通道。

---

## 1. 功能需求 → 系统能力映射

| 需求编号 | 需求描述                              | 最终实现机制                                    |
| ---- | --------------------------------- | ----------------------------------------- |
| (0)  | 因子模板 + 评价工具 mock                  | 模板渲染工具 + mock_evals 工具层                   |
| (1)  | 根据描述按模板生成代码                       | `gen_code_react` ReAct 生成                 |
| (2)  | 试运行失败/语义不符 ReAct 重试≤5             | dryrun + semantic_check + retry_count 控制  |
| (3)  | 生成后人工审核，可修改确认                     | `human_review_gate` 触发 AG-UI `ui_request` |
| (4)  | 审核通过后回填 + 评价入库                    | backfill_and_eval + write_db（mock）        |
| (5)  | LangGraph Agent + 标准事件，FastAPI 暴露 | ag-ui-langgraph 一键 SSE                    |
| (6)  | AG-UI 协议前后端通道，CopilotKit 展示       | CopilotKitProvider + AG-UI event render   |

---

## 2. 后端 MVP 设计

### 2.1 State（最终版）

> 使用 LangGraph `MessagesState` 做消息管理 + 扩展业务字段。
> 所有节点输出用 `Command(goto=..., update=...)` 路由，消除前后阶段冲突。

```python
# backend/graph/state.py
from langgraph.graph import MessagesState

class FactorAgentState(MessagesState):
    # 流程路由与控制
    route: str = "collect_spec"
    should_interrupt: bool = False
    retry_count: int = 0                 # 全局重试计数（<=5）
    system_date: str | None = None

    # 用户需求与产物
    user_spec: str = ""                  # 因子自然语言描述
    factor_name: str | None = None
    factor_code: str | None = None       # 模板化完整因子代码

    # 上下文稳态
    overwrite_fields: list[str] = []     # 显式声明需要覆盖/置空的字段
    short_summary: str | None = None     # 会话短摘要，跨节点维持稳态

    # 校验结果
    dryrun_result: dict | None = None    # {ok, stdout, stderr, traceback}
    semantic_check: dict | None = None   # {ok, diffs, reason}

    # HITL
    human_review_status: str = "pending" # pending/edited/approved/rejected
    human_edits: str | None = None       # 人工修改后的完整代码

    # 回填/评价/入库
    eval_metrics: dict | None = None     # mock 评价结果
    backfill_job_id: str | None = None
    db_write_status: str | None = None

    # 工件区（可供前端下载/展示）
    artifacts: dict = {}                 # {code, logs, reports, preview_stats}
```

#### 消息滑窗/摘要策略

* 保留最近 K 条消息（建议 K=12）作为主上下文。
* 每次阶段切换（如进入 HITL / 回填）前做一次 `short_summary`，写入 state，供后续 ReAct 修复稳定语义。
* 所有模型调用统一拼为：`[system_msg] + last_K_messages + short_summary_hint`

---

### 2.2 节点输出模型（Pydantic）

> 保证每个节点的输出结构稳定，便于评估、日志与前端渲染。

```python
class IntentAction(BaseModel):
    human_input: bool = False
    message: str | None
    factor_name: str | None
    constraints: dict = {}

class CodeGenAction(BaseModel):
    human_input: bool = False
    message: str | None
    factor_code: str | None
    reflect_notes: str | None

class DryRunResult(BaseModel):
    ok: bool
    stdout: str = ""
    stderr: str = ""
    traceback: str = ""

class SemanticCheckResult(BaseModel):
    ok: bool
    diffs: list[str] = []
    reason: str | None = None

class HumanReviewAction(BaseModel):
    status: str  # approved/edited/rejected
    edited_code: str | None = None

class BackfillAction(BaseModel):
    ok: bool
    job_id: str | None = None
    preview_stats: dict = {}

class EvalAction(BaseModel):
    ok: bool
    metrics: dict = {}

class PersistAction(BaseModel):
    ok: bool
    uri: str | None = None
    rows_written: int = 0
```

---

### 2.3 工具层（模板 + 沙盒 + 评价 + 入库，均可替换）

#### 2.3.1 因子模板（最终定义）

* LLM 只填 `{factor_body}`，其余由模板固化。
* 强制：输入 df 的 index/columns 约定、返回 Series 对齐。

```python
FACTOR_TEMPLATE = """
# Factor: {factor_name}
# Description: {user_spec}

import pandas as pd
import numpy as np

def load_data(start: str, end: str, universe: list[str]) -> pd.DataFrame:
    # TODO: will be replaced by real loader
    raise NotImplementedError

def compute_factor(df: pd.DataFrame) -> pd.Series:
    # df index: [date, symbol]
    # df columns: include required fields from user_spec/constraints
    # return: pd.Series indexed like df
    {factor_body}

def run_factor(start, end, universe):
    df = load_data(start, end, universe)
    fac = compute_factor(df)
    return fac
"""
```

#### 2.3.2 工具接口（mock → 可平滑替换）

```python
def render_factor_template(factor_name, user_spec, factor_body) -> str: ...
def run_code(code: str, entry="run_factor", args=None) -> dict: ...
def evaluate_factor(values, spec) -> dict: ...
def write_factor_and_metrics_mock(name, metrics, values_artifact) -> dict: ...
```

#### 2.3.3 沙盒安全护栏

* 禁网、禁文件系统写、禁危险模块。
* AST 白名单检查（如仅允许 pandas/numpy/scipy）。
* CPU/内存/时间配额（避免死循环/爆内存）。

---

### 2.4 ReAct 代理（create_react_agent）

节点：`gen_code_react`

**工具**

1. `CodeGenTool(factor_template, user_spec, constraints) -> factor_body`
2. `ErrorFixTool(prev_code, dryrun_error, semantic_diffs, short_summary) -> factor_body`

**输入拼装（每轮）**

* user_spec
* constraints（从 collect_spec 抽取）
* 上次 factor_code
* dryrun traceback（若有）
* semantic diffs（若有）
* short_summary

**重试控制（统一放到 graph，而不是 prompt 里）**

* `retry_count` 由节点维护
* 失败则 `retry_count += 1`
* `retry_count >= 5` → 强制 `should_interrupt=True`，跳 HITL

---

### 2.5 LangGraph 控制流（最终图）

**节点**

1. `collect_spec`：抽取因子名 + 约束（窗口、字段、频率、口径）
2. `gen_code_react`：ReAct 生成模板化因子代码
3. `dryrun`：沙盒试运行最小样例
4. `semantic_check`：语义一致性检查
5. `react_retry_router`：失败 → 修复重试 / 超限 → HITL
6. `human_review_gate`：人工审核编辑确认
7. `backfill_and_eval`：历史回填 + mock 评价
8. `write_db`：mock 入库
9. `finish`：输出汇总/提示下一步

**边**

* `collect_spec -> gen_code_react -> dryrun -> semantic_check -> react_retry_router`
* `react_retry_router`

  * pass → `human_review_gate`
  * fail & retry_count<5 → `gen_code_react`
  * fail & retry_count>=5 → `human_review_gate`（should_interrupt=True）
* `human_review_gate`

  * approved/edited → `backfill_and_eval -> write_db -> finish`
  * rejected → `finish`

---

### 2.6 HITL（Human-in-the-Loop）事件流

节点：`human_review_gate`

**后端行为**

* 发 AG-UI `ui_request`（类型 `code_review`）
* graph stop & wait
* 收到 `ui_response` 后更新：

  * `human_review_status`
  * `human_edits`
  * `factor_code`

---

### 2.7 AG-UI 标准事件规范（最终）

> 所有节点都通过标准事件向前端透传状态与轨迹。

* `assistant_message`

  * `{content, markdown: true}`
* `state_update`

  * `{route, retry_count, should_interrupt, factor_name, factor_code?, eval_metrics?, db_write_status?}`
* `tool_call` / `tool_result`

  * call：`{name, input}`
  * result：`{name, output, ok}`
* `ui_request` / `ui_response`

  * request：`{type:"code_review", code, notes, actions:[approve, edit, reject]}`
  * response：`{status, edited_code?}`
* `interrupt`

  * `{"exceeded_retries": true, "errors": [...]}`
* `progress`

  * `{"stage":"backfill|evaluate|write_db", "pct":0-100}`

---

### 2.8 FastAPI 暴露（ag-ui-langgraph）

```python
from fastapi import FastAPI
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from graph.graph import graph

app = FastAPI()
add_langgraph_fastapi_endpoint(app, graph, "/agent")

@app.get("/health")
def health():
    return {"ok": True}
```

可选：

* `/artifacts/{id}`：下载代码/日志/报告工件

---

### 2.9 agentevals 离线评估（CI 回归）

**数据集**

* `eval/dataset.jsonl`：`{user_spec, expected_ops, expected_fields}`

**评估器**

1. 轨迹合理性：是否按预期调用 `gen->dryrun->semantic->hitl->backfill`
2. 可运行率：dryrun ok / backfill ok
3. 语义对齐：LLM judge 0~1 分

**CI 要求**

* prompt/tools/graph 任一变更 → 必跑评估
* 设置最低阈值（如运行率 ≥ 0.8）

---

## 3. 前端 MVP 设计（CopilotKit + AG-UI）

### 3.1 页面结构（最终）

`/factor-copilot`

* 左侧：CopilotChat（对话 + trace）
* 右侧：

  * CodeReviewPanel（HITL popup）
  * MetricsPanel（展示 eval_metrics）
* 顶部 badge：`running / waiting_human / done`

---

### 3.2 CopilotKit 连接 LangGraph SSE

* `CopilotKitProvider`
* `useCopilotChat({ apiEndpoint: "/agent" })`
* CopilotKit 自动消费 AG-UI 事件。

---

### 3.3 事件 → UI 映射（最终）

| 事件                      | UI 行为                |
| ----------------------- | -------------------- |
| assistant_message       | 聊天气泡流式渲染             |
| tool_call/tool_result   | TracePane 步骤卡片       |
| state_update            | 刷新右侧面板/顶部 badge      |
| ui_request(code_review) | 打开 Monaco 编辑器 + 操作按钮 |
| ui_response             | 发送回后端并锁定面板           |
| progress                | 长任务进度条               |
| interrupt/error         | 错误提示 + 引导人工处理        |

---

## 4. 端到端运行序列（终稿）

1. 用户输入因子描述
2. `collect_spec` 结构化：因子名/字段/窗口/口径
3. `gen_code_react` 生成模板化代码
4. `dryrun` 沙盒最小样例试跑
5. `semantic_check` 对齐描述语义
6. 若失败 → `react_retry_router` 回 `gen_code_react` 重试（≤5）
7. 进入 `human_review_gate` → 前端编辑确认
8. 审核通过 → `backfill_and_eval`（历史回填 + mock 评价）
9. `write_db` mock 入库
10. `finish` 总结输出、提供工件下载/下一步建议

---

## 5. 交付目录结构（最终）

**backend/**

```
backend/
  app.py
  graph/
    state.py
    nodes.py
    tools/
      factor_template.py
      sandbox_runner.py
      mock_evals.py
      mock_db.py
    graph.py
  prompts/
    codegen_system.md
    reflect_fix.md
    semantic_judge.md
  eval/
    dataset.jsonl
    run_eval.py
```

**frontend/**

```
frontend/
  app/factor-copilot/page.tsx
  components/
    CopilotChatPane.tsx
    TracePane.tsx
    CodeReviewPanel.tsx
    MetricsPanel.tsx
    StatusBadge.tsx
```

---

## 6. 实施清单（按这个顺序开干）

1. 定义终版 `FactorAgentState` + 消息滑窗/摘要策略
2. 实现节点（Intent/CodeGen/DryRun/Semantic/HITL/Backfill/Eval/DB）
3. 封装工具层 mock（模板渲染/沙盒/评价/入库）
4. 集成 create_react_agent + CodeGen/ErrorFix 工具
5. 加入 retry_count 路由与 `should_interrupt` 强制 HITL
6. 接 ag-ui-langgraph 暴露 `/agent` SSE
7. 前端 CopilotKit 接入，先渲染 chat/trace
8. 加 CodeReviewPanel 实现 `ui_request/ui_response` HITL
9. 加 MetricsPanel 展示 mock eval_metrics
10. 引入 agentevals 数据集 + CI 回归阈值门控

---

如果你要我继续，我可以在下一条直接给你：

* 按上述终稿实现的 **LangGraph graph.py / nodes.py / tools mock** 代码骨架（可直接复制跑）
* 以及 **CopilotKit + AG-UI + HITL 前端最小 demo**。
