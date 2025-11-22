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


# 项目方案

下面给你一个可落地的 MVP 设计方案（后端 / 前端分开），尽量“用现成的轮子”：LangGraph + create_react_agent、agentevals、ag-ui-langgraph（=你提到的 ai-ui-langgraph 方向）、CopilotKit + AG-UI 协议。整体目标是：快速搭一个“量化选股因子编码助手”原型，可跑通从描述→生成→自测→ReAct 重试→人工审核→批量计算&评价→入库→前端可观测的闭环。

---

## 0. 总体框架选型（尽量复用开源成熟方案）

**后端**

* **LangGraph**：做工作流/状态机编排。
* **langgraph.prebuilt.create_react_agent**：用于“代码生成 + 工具调用 + 反思重试”的 ReAct 代理快速搭建。([CSDN Blog][1])
* **agentevals / agent-evals**：基于 LangSmith 的现成 agent 轨迹评估框架，先用 mock 数据集做自动回归评测。([GitHub][2])
* **ag-ui-langgraph**：官方 CopilotKit 维护的 LangGraph ↔ AG-UI 协议集成包，一行把 graph 暴露成 FastAPI SSE 事件流服务。([PyPI][3])
* **FastAPI**：API / SSE / 鉴权 / 入库等。

**前端**

* **Next.js / React**：CopilotKit 推荐的主栈。
* **CopilotKit**：直接消费 AG-UI SSE 事件、渲染对话与“生成式 UI / HITL UI”。([copilotkit.ai][4])
* **AG-UI Protocol**：前后端标准事件 & 状态传输协议。([copilotkit.ai][4])

---

## 1. 后端 MVP 方案

### 1.1 核心状态（LangGraph State）

用 Pydantic 定义一个 `FactorAgentState`（继承 `MessagesState` 或 CopilotKitState），最小状态如下：

```python
class FactorAgentState(MessagesState):
    user_spec: str                      # 用户因子描述（自然语言）
    factor_name: str | None
    factor_code: str | None             # 生成的因子 python 代码（模板化）
    retries_left: int = 5               # ReAct 重试次数
    dryrun_result: dict | None          # 试运行结果/报错
    semantic_check: dict | None         # 与用户描述一致性检查结果
    human_review_status: str = "pending" # pending/edited/approved/rejected
    human_edits: str | None
    eval_metrics: dict | None           # 因子评价（mock）
    backfill_job_id: str | None         # 历史回填任务 id
    db_write_status: str | None         # 入库状态
```

> 这个 state 会被 ag-ui-langgraph 自动映射/流式推送到前端（state_update 等事件）。

---

### 1.2 工具层（先 mock）

#### （0）因子模板 & 工具函数

准备两套东西：

1. **因子模板（Factor Template）**
   统一输入/输出约束，便于 LLM 生成“可插拔因子”。

```python
FACTOR_TEMPLATE = """
# Factor: {factor_name}
# Description: {user_spec}

import pandas as pd
import numpy as np

def load_data(start: str, end: str, universe: list[str]) -> pd.DataFrame:
    # TODO: replaced by real loader
    raise NotImplementedError

def compute_factor(df: pd.DataFrame) -> pd.Series:
    # df index: [date, symbol], columns include required fields
    # return: factor values aligned to df index
    {factor_body}

def run_factor(start, end, universe):
    df = load_data(start, end, universe)
    fac = compute_factor(df)
    return fac
"""
```

2. **因子评价工具（mock 版）**

* `factor_ic_mock(fac, fwd_ret)`
* `factor_turnover_mock(fac)`
* `factor_group_perf_mock(fac, fwd_ret)`
* `write_factor_and_metrics_mock(...)`

> 这些先返回固定结构（或随机/简单统计），后续替换成真实生产逻辑即可。

---

### 1.3 LangGraph 控制流（节点与边）

下面是满足你 0~6 需求的最小图（MVP）：

**节点**

1. `collect_spec`：接收用户输入 → 结构化 user_spec / factor_name
2. `gen_code_react`：create_react_agent 生成因子代码（按模板）
3. `dryrun`：在 sandbox/容器里跑 `compute_factor` 的最小样例
4. `semantic_check`：LLM judge or rule-based，对齐用户描述
5. `react_retry_router`：dryrun 或 semantic 不通过 → 触发 ReAct “反思+修复”
6. `human_review_gate`：进入 HITL，前端提供编辑/确认
7. `backfill_and_eval`：历史回填 + mock 评价
8. `write_db`：结果入库（mock）
9. `finish`

**边（简化版）**

* `collect_spec -> gen_code_react -> dryrun -> semantic_check`
* `semantic_check -> react_retry_router`
* `react_retry_router`

  * 如果通过：`-> human_review_gate`
  * 如果失败且 retries_left>0：`-> gen_code_react`（携带错误/反思上下文）
  * 如果失败且 retries_left==0：`-> human_review_gate`（标记“需人工救援”）
* `human_review_gate`

  * approved：`-> backfill_and_eval -> write_db -> finish`
  * rejected：`-> finish`
  * edited：更新 factor_code 后 `-> backfill_and_eval ...`

> 这样就满足（1）（2）（3）（4）（5）。

---

### 1.4 ReAct 代理设计（create_react_agent）

`gen_code_react` 用 **prebuilt ReAct agent**，配两类工具：

* **CodeGen Tool**（内部 tool，不对外暴露）：给 LLM 因子模板 + 用户 spec → 输出 `{factor_body}`
* **ErrorFix Tool**：接受 dryrun 堆栈、semantic_check diff → 生成补丁式修复（重新走模板）

create_react_agent 支持工具调用 + 思考 + 记忆/检查点。([CSDN Blog][1])

MVP 里建议：

* system prompt 固化模板约束
* memory/checkpointer 记录每次失败原因
* 每次迭代都把 **“上次代码 + 失败信息 + 用户约束”** 放进输入，避免漂移

---

### 1.5 Human-in-the-Loop 事件流

**为什么用 AG-UI+CopilotKit HITL？**
CopilotKit 对 LangGraph 的 HITL 有现成“工具调用 UI / 人类确认 UI / state 共享”套路。([DogAPI-人工智能接口商城][5])

**后端实现**

* 在 `human_review_gate` 节点里发出 AG-UI 标准事件：

  * `ui_request` / `input_required`（让前端弹“代码编辑器 + diff + 审核按钮”）
* 暂停 graph：等待前端用 `ui_response` 把结果回传。
* state 更新：

  * `human_review_status`
  * `human_edits`（如果有）
  * `factor_code = edited_code or original_code`

---

### 1.6 FastAPI 暴露（ag-ui-langgraph）

`ag-ui-langgraph` 已经把 **LangGraph 变成带 AG-UI SSE 事件流的 FastAPI endpoint**，基本不用自己写协议层。([PyPI][3])

MVP 代码骨架：

```python
from fastapi import FastAPI
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from my_graph import graph  # 你定义的 StateGraph.compile()

app = FastAPI()
add_langgraph_fastapi_endpoint(app, graph, "/agent")  # SSE + AG-UI events
```

---

### 1.7 agentevals 评估（离线/CI）

MVP 评估目标：

* 输入一组因子描述 → 期望生成某类算子/字段
* 评估维度：

  1. **工具轨迹是否合理**（trajectory evaluator）
  2. **最终代码可运行率**
  3. **语义对齐评分**（LLM-as-judge）

agentevals 提供“dataset → RemoteGraph invoke → evaluator 打分 → LangSmith 记录”的标准流程，你只需要写：

* `transform_dataset_inputs`
* `transform_agent_outputs`
* 一个或多个 evaluators（先 mock）([GitHub][2])

最好在 CI 里每次改 prompt / tool 都跑一次回归。

---

## 2. 前端 MVP 方案（CopilotKit + AG-UI）

### 2.1 页面结构

一个最小 Next.js app：

* `/factor-copilot` 页面

  * 左侧：Chat / agent trace（CopilotChat）
  * 右侧：动态 UI 面板（CodeReviewPanel / MetricsPanel）
  * 顶部：当前状态 badge（running / waiting_human / done）

### 2.2 CopilotKit 接 LangGraph

复制 CopilotKit 官方“LangGraph + AG-UI”接法：

* `CopilotKitProvider`
* `useCopilotChat()` 连接 `/agent` SSE
* 自动渲染 `assistant_message / tool_call / state_update / ui_request` 等事件。([copilotkit.ai][4])

### 2.3 前端对标准事件的呈现策略

**AG-UI 标准事件 → UI 行为**（MVP）

* `assistant_message`：对话流式输出
* `tool_call` / `tool_result`：显示“步骤卡片”（因子生成 / dryrun / 评价 / 入库）
* `state_update`：更新右侧面板数据、顶部 badge
* `ui_request`（human_review_gate 发的）：

  * 弹出 `CodeReviewPanel`
  * panel 内：

    * Monaco Editor（显示 `factor_code`）
    * “通过 / 修改后通过 / 驳回” 3 按钮
  * 用户点击后 → 发 `ui_response` 回后端（含 edited_code & status）

CopilotKit 对“生成式UI / HITL”都有示例套路，可直接复用。([DogAPI-人工智能接口商城][5])

---

## 3. 端到端事件/控制流（含 HITL）

下面按时间顺序描述一次完整运行（对齐你的 0~6）：

1. **用户输入**

   * 前端 `CopilotChat` 发送 `user_message`
   * 后端 `collect_spec` 写入 `user_spec`、产出结构化因子名（可 LLM 轻抽）

2. **生成代码（模板化）**

   * `gen_code_react` 调 create_react_agent
   * 产出 `factor_code`
   * 事件：`assistant_message` + `state_update(factor_code=...)`

3. **试运行 dryrun**

   * `dryrun` 工具执行（mock 数据）
   * 成功则继续；失败写 `dryrun_result(error=...)`
   * 事件：`tool_call(dryrun)` → `tool_result`

4. **语义对齐检查**

   * `semantic_check`：LLM judge / 规则比对
   * 不通过写 `semantic_check(diff=...)`

5. **ReAct 重试（最多 5 次）**

   * `react_retry_router` 判断：

     * fail & retries_left>0 → `assistant_message(reflect)` + `state_update(retries_left-1)` → 回 `gen_code_react`
     * pass → 进入下一步

6. **人工审核 HITL**

   * `human_review_gate` 发 `ui_request(code_review)`
   * 前端打开编辑/确认面板
   * 用户：

     * approve → `ui_response(status=approved)`
     * edit → `ui_response(status=edited, edited_code=...)`
     * reject → `ui_response(status=rejected)`
   * 后端接收后更新 state

7. **历史回填 + 因子评价**

   * `backfill_and_eval`：

     * 运行 `run_factor(start,end,universe)`
     * 调 mock 评价函数算 IC/分组/换手等
   * `eval_metrics` 写入 state
   * 事件：`tool_call(backfill)` / `tool_result(metrics)`

8. **结果入库**

   * `write_db`（mock）
   * `db_write_status=success`
   * 事件：`tool_call(write_db)` / `tool_result`

9. **结束**

   * `finish` 发最终总结 + 引导下一因子

---

## 4. MVP 目录与交付物建议

**后端 repo**

```
backend/
  app.py                    # FastAPI + ag-ui-langgraph endpoint
  graph/
    state.py
    nodes.py
    tools/
      factor_template.py
      mock_data_loader.py
      mock_evals.py
    graph.py                # StateGraph 编排 & compile
  prompts/
    codegen_system.md
    reflect_fix.md
    semantic_judge.md
  eval/
    dataset.jsonl
    run_eval.py             # agentevals 入口
```

**前端 repo**

```
frontend/
  app/factor-copilot/page.tsx
  components/
    CopilotChatPane.tsx
    TracePane.tsx
    CodeReviewPanel.tsx     # HITL 编辑确认
    MetricsPanel.tsx
```

---

## 5. 你可以立刻按这个顺序开工

1. 后端把 **模板 + mock 工具 + graph 控制流跑通**
2. 接上 `ag-ui-langgraph` SSE endpoint
3. 前端用 CopilotKit 接 `/agent`，先只显示聊天与 trace
4. 加 `ui_request/ui_response`，完成 HITL 审核
5. 接 `agentevals` 做离线评测与 CI

---