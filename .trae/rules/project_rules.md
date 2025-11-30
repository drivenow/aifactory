我要实现以下短期和中期的改造：
短期（现在）

后端继续保持 单一 FactorAgentGraph：

所有节点串在一张图里

state 用一个 FactorAgentState

前端只暴露一个 factor_agent CoAgent（你已经是这样）

命令行调试：

新增一个 cli_debug.py，复用同一个 graph，用 GraphInterrupt + Command(resume) 写个简单 loop 即可

不修改任何节点 / Graph 定义

中期（下一步演进）

把“逻辑生成 / 代码生成 / 评估”等节点背后的逻辑抽成 Python 纯函数

在需要的地方（别的服务 / Cron / 脚本）可以直接调这些函数，不一定每次都走 graph

如果有“只跑逻辑”这类 API，就用 Command(goto="logic_node") 之类的方式，给 Graph 提供多入口


好，直接给你一份可以丢给 Codex 的“改造需求 & 实施计划”。

---

## 0. 总体目标

1. **后端只有一份 LangGraph 图定义**

   * 同一份 `graph` 同时给：

     * CopilotKit / 前端调用
     * 命令行 CLI 调试调用
   * 节点逻辑 / State 类型不再因为“前端 vs CLI”而分叉。

2. **能力模块化**

   * 将“逻辑生成 / 代码生成 / 评估”等封装成可复用模块（函数或子图），
   * FactorAgent 大图只是 orchestrator，把这些能力串起来。
   * 将来需要单独暴露“逻辑生成”/“代码生成”能力时，不需要大改，只包一层薄壳。

---

## 1. 代码结构改造要求

### 1.1 新建/整理后端模块结构（建议）

```text
backend/
  factor_agent/
    __init__.py
    graph.py              # ✅ 唯一的 LangGraph 定义出口（主图）
    state.py              # ✅ FactorAgentState + 各子 state 类型
    domain/
      logic.py            # ✅ 逻辑生成能力（纯函数/子图）
      codegen.py          # ✅ 代码生成能力（纯函数/子图）
      eval.py             # ✅ 因子评估能力（纯函数/子图）
      review.py           # ✅ 人审相关辅助（如果需要）
    cli_debug.py          # ✅ 命令行调试入口
  api/
    copilotkit_route.py   # ✅ CopilotKit /api/copilotkit 实现，复用 factor_agent.graph
```

**要求：**

* `factor_agent/graph.py` 导出 **一个编译后的 graph 对象**：`graph: CompiledGraph[FactorAgentState]`。
* `state.py` 里定义 `FactorAgentState` 以及若干子状态类型（见下文）。
* `domain/*.py` 不直接依赖 HTTP/前端，只依赖 State / LLM 客户端等。

---

## 2. Graph 统一定义改造

### 2.1 抽出 graph 定义

**目标：**把当前所有节点 / 边 / checkpointer 的定义集中到 `factor_agent/graph.py`，示意：

```python
# factor_agent/graph.py
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver  # 之后可换成持久版
from .state import FactorAgentState
from .domain.logic import logic_node
from .domain.codegen import codegen_node
from .domain.eval import backfill_and_eval_node
from .domain.review import human_review_gate

builder = StateGraph(FactorAgentState)

builder.add_node("logic", logic_node)
builder.add_node("codegen", codegen_node)
builder.add_node("human_review_gate", human_review_gate)
builder.add_node("backfill_and_eval", backfill_and_eval_node)
# ... 其他节点 & 边 ...

checkpointer = MemorySaver()  # TODO: 后续可按环境切换
graph = builder.compile(checkpointer=checkpointer)
```

**Codex 实现要点：**

1. 确保所有原来散落在别处的节点函数都迁移到 `domain/` 或 `graph.py` 中引用。
2. 对 CopilotKit 路由 & CLI 调试都统一从 `factor_agent.graph` import `graph`。
3. 暂时保持现有 checkpointer 不变（方便对比回归），后续再按环境拆分。

---

## 3. 命令行调试入口改造

### 3.1 新建 `factor_agent/cli_debug.py`

**目标：**命令行下可以直接跑完整 FactorAgentGraph，支持 `interrupt` → CLI 输入 → `Command(resume=...)` 的流程。

**具体要求：**

* 使用和前端相同的 `graph` 对象：

  ```python
  from .graph import graph
  ```
* 每次 CLI 调试创建一个新的 `thread_id`，例如 `cli-{uuid}`。
* `invoke` 调用中捕获 `GraphInterrupt`，打印 payload 后从 `input()` 读用户输入，再用 `Command(resume=...)` 继续。

**Codex 可按以下模板实现：**

```python
# factor_agent/cli_debug.py
import uuid
import json
from langgraph.errors import GraphInterrupt
from langgraph.types import Command
from .graph import graph

def cli_debug():
  thread_id = f"cli-{uuid.uuid4()}"
  config = {"configurable": {"thread_id": thread_id}}

  # TODO: 根据实际 State 填一个合理的 init_state
  current_input = {
      "messages": [
          {"role": "user", "content": "帮我设计一个量化因子"}
      ],
      "retry_count": 0,
      # 其他必要的初始字段
  }

  while True:
      try:
          result = graph.invoke(current_input, config=config)
          print("\n✅ Graph finished.")
          print(json.dumps(result, ensure_ascii=False, indent=2))
          break
      except GraphInterrupt as gi:
          payload = gi.value
          print("\n⏸️  Graph interrupted. Payload:")
          print(json.dumps(payload, ensure_ascii=False, indent=2))

          s = input("\n请输入 resume 值（回车=True；JSON 自动解析）：\n> ").strip()
          if s == "":
              resume_val = True
          else:
              try:
                  resume_val = json.loads(s)
              except json.JSONDecodeError:
                  resume_val = s

          current_input = Command(resume=resume_val)

if __name__ == "__main__":
  cli_debug()
```

**验收标准：**

* 在项目根目录 `poetry run python -m factor_agent.cli_debug` 能跑通：

  * 完整流程能走完；
  * 命中 `human_review_gate` 时能在命令行看到中断 payload，并通过输入完成 resume。

---

## 4. State 结构改造（便于后续拆分能力）

### 4.1 在 `state.py` 中拆分子状态类型

**目标：**`FactorAgentState` 是多个子领域 State 的组合，利于将来拆成独立 agent / 子图。

**要求示意：**

```python
# factor_agent/state.py
from typing_extensions import TypedDict

class LogicState(TypedDict, total=False):
    logic_prompt: str
    logic_spec: str

class CodeGenState(TypedDict, total=False):
    code_prompt: str
    factor_code: str

class EvalState(TypedDict, total=False):
    eval_metrics: dict

class HumanReviewState(TypedDict, total=False):
    human_review_status: str
    ui_request: dict
    ui_response: dict
    retry_count: int

class FactorAgentState(
    LogicState,
    CodeGenState,
    EvalState,
    HumanReviewState,
    total=False,
):
    db_write_status: str
    last_success_node: str
    route: str
```

**Codex 注意：**

* 把现在所有用到的字段整理归类到这些子 State 里；
* 避免到处用 `state["xxx"]` 的魔法字符串，尽量统一命名；
* 不改动字段含义，只做结构归类和类型声明。

前端 TS 里的 `FactorAgentState` 类型保持和这里对齐（你现在已经有一版 TS 声明，Codex 需要同步更新）。

---

## 5. 节点逻辑模块化改造

### 5.1 把大块逻辑拆到 `domain/*.py`

**目标：**节点函数只是 State ↔ domain 函数的“适配层”，真正的业务能力在 `domain` 里。

**示意：**

```python
# domain/logic.py
from ..state import FactorAgentState

def generate_logic(state: FactorAgentState) -> FactorAgentState:
    # 调 LLM 生成逻辑描述，写回 logic_spec 等
    ...
    return {
        "logic_spec": "...",
        "logic_prompt": "...",
    }

def logic_node(state: FactorAgentState) -> FactorAgentState:
    return generate_logic(state)
```

```python
# domain/codegen.py
from ..state import FactorAgentState

def generate_code(state: FactorAgentState) -> FactorAgentState:
    # 调 LLM / 工具生成因子代码
    ...
    return {
        "factor_code": "...",
        "code_prompt": "...",
    }

def codegen_node(state: FactorAgentState) -> FactorAgentState:
    return generate_code(state)
```

```python
# domain/eval.py
def backfill_and_eval_node(state: FactorAgentState) -> FactorAgentState:
    # 回测 + 评估，写 eval_metrics / db_write_status 等
    ...
```

```python
# domain/review.py
from langgraph.types import Command
from langgraph.types import interrupt

def human_review_gate(state: FactorAgentState) -> Command:
    # 你现有的 interrupt 逻辑，搬到这里
    ...
```

**要求：**

* 所有大块逻辑都抽成独立函数，便于以后：

  * 直接在别的服务里调用（不走 LangGraph）；
  * 或给它们再包一个小 graph 单独暴露。

---

## 6.（可选）为单个能力准备“小 graph” 模板

这一条可以先列为“后续可选任务”，不一定现在做：

**目标：**如果以后要单独暴露“逻辑生成 agent”、“代码生成 agent”，能快速起一个小 graph。

**模板要求：**

```python
# factor_agent/small_graphs.py
from langgraph.graph import StateGraph
from .state import LogicState, CodeGenState
from .domain.logic import logic_node
from .domain.codegen import codegen_node

logic_builder = StateGraph(LogicState)
logic_builder.add_node("logic", logic_node)
logic_builder.add_edge("__start__", "logic")
logic_builder.add_edge("logic", "__end__")
logic_graph = logic_builder.compile(checkpointer=...)  # 可以是简单 MemorySaver

codegen_builder = StateGraph(CodeGenState)
codegen_builder.add_node("codegen", codegen_node)
codegen_builder.add_edge("__start__", "codegen")
codegen_builder.add_edge("codegen", "__end__")
codegen_graph = codegen_builder.compile(checkpointer=...)
```

后续再根据需要：

* 在 API 层新增 `/api/logic_agent` / `/api/codegen_agent`；
* 复用 CopilotKit 的同一套 runtime，只是 agent 名字不同。

---

## 7. 验收 checklist（给你和 Codex 对齐）

1. **Graph 统一：**

   * [ ] `factor_agent/graph.py` 存在，并导出 `graph`。
   * [ ] API / CopilotKit 路由不再自己定义 graph，只是 import。
   * [ ] CLI 调试也从这里 import `graph`。

2. **命令行调试：**

   * [ ] `poetry run python -m factor_agent.cli_debug` 能跑通完整流程。
   * [ ] 若 workflow 中有 `interrupt`，在 CLI 能看到 payload & 正常 resume。

3. **State 归类：**

   * [ ] `state.py` 中有清晰的 `LogicState` / `CodeGenState` / `EvalState` / `HumanReviewState` / `FactorAgentState`。
    LogicState = {"logic_spec": "...", "logic_prompt": "..."}
    CodeGenState = {"factor_code": "...", "code_prompt": "..."}
    EvalState = {"eval_metrics": {...}}
    HumanReviewState = {"human_review_status": "approve", "retry_count": 1}

    FactorAgentState = 以上所有键的并集（同一层）

   * [ ] 所有节点只读写自己需要的字段，字段命名和前端 TS 类型对齐。

4. **逻辑模块化：**

   * [ ] 逻辑生成、代码生成、评估、人审等核心逻辑在 `domain/*.py` 中有对应函数。
   * [ ] graph 节点本身比较“薄”，主要工作是调用这些 domain 函数。

5. **前端兼容：**

   * [ ] 原有的 `<CopilotKit runtimeUrl="/api/copilotkit" agent="factor_agent">` 不需要改。
   * [ ] `useCoAgent<FactorAgentState>` 仍能拿到和之前语义一致的字段（只是类型结构更清晰）。

---

你可以把上面这份直接贴给 Codex，当成“重构任务说明书”。
如果 Codex 实现过程中某一步有争议（比如 checkpointer 换不换、是否现在就加小 graph），你可以随时把它生成的代码或方案贴回来，我可以帮你做 code review 和进一步简化。
