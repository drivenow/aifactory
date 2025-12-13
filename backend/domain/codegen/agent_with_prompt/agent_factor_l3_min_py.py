from __future__ import annotations

from typing import Any, Optional
import time
from langchain_core.messages import HumanMessage, SystemMessage
from domain.codegen.framework.factor_l3_py_min_standard import (
    PROMPT_FACTOR_L3_PY_RULE,
    PROMPT_FACTOR_L3_PY_MIN_1S,
    PROMPT_FACTOR_L3_PY_DEMO_SAMPLE,
    PROMPT_FACTOR_L3_PY_DEMO,
    PY_NONFACTOR_META,
    PY_NONFACTOR_PATH
)
from domain.codegen.framework.factor_l3_py_tool import (
    l3_syntax_check,
    l3_mock_run,
)
from domain.codegen.framework import (
    l3_mock_run,
    l3_syntax_check,
)
from domain.codegen.view import CodeGenView
from domain.llm import _extract_last_assistant_content, _unwrap_agent_code, create_agent


PROMPT_FACTOR_L3_PY = """你是一个量化高频因子工程师助手，使用 Python 和 L3FactorFrame 框架开发因子。

你的任务是：根据用户给出的文字需求或参考代码，生成 可直接在 L3 因子框架中运行的因子代码。

# 【一、基础框架约束】
""" + PROMPT_FACTOR_L3_PY_RULE + """

# 【二、数据访问与因子类型】
你需要根据用户需求自动判断该因子更适合用哪种数据路径：
- 逐笔 L3 因子：直接使用 getPrevTick / getPrevNTick / getPrevSecTrade 等接口；
- 采样 1min 因子：通过 self.get_factor_instance("FactorSecXXX") 获取 nonfactor，访问其中的列表字段。

在本框架中，绝大多数业务因子不会直接在 calculate 中从逐笔数据开始算，而是依赖「分钟级 nonfactor」：

### 1. L3 逐笔因子数据接口示例（直接用逐笔）

逐笔因子直接从 L3 数据接口采数，典型写法如下（`ActivePriceVolume` 示例）：

""" + PROMPT_FACTOR_L3_PY_DEMO + """


当用户需求明显是“基于逐笔 tick / 逐笔成交的微观行为”，且没有要求 1min 聚合时，可以采用这种 **逐笔因子模式**。

### 2. 采样 1min 的 nonfactor（作为依赖，不由你改写）

采样 1min 的聚合逻辑在 nonfactor 中定义，你只负责**读取 nonfactor 的输出**。

以 `FactorSecOrderBook` 为例（nonfactor，本身也是 FactorBase 子类）：

```python
class FactorSecOrderBook(FactorBase):
    def __init__(self, config, factorManager, marketDataManager):
        super().__init__(config, factorManager, marketDataManager)

        self.lag = 120
        self.last_px_list = []
        self.high_px_list = []
        self.low_px_list = []
        ...

    def calculate(self):
        sample_1s_flag = self.get_sample_flag()
        if not sample_1s_flag and self.factorManager.mode == "SAMPLE_1S":
            self.addFactorValue(None)
            return

        self.last_px_list.append(self.getPrevTick("LastPrice"))
        self.high_px_list.append(self.getPrevTick("HighPrice"))
        self.low_px_list.append(self.getPrevTick("LowPrice"))
        ...
```

你**不需要**也**不允许**在业务因子中再去重写这些采样逻辑，只要通过 `get_factor_instance` 拿到 nonfactor，并读它维护的 `xxx_list` 即可。

### 3. 采样 1min 的业务因子（通过 nonfactor 取数）

业务因子例子（`FactorBuyWillingByPrice`），依赖 `FactorSecTradeAgg` 这个 nonfactor：

**注意：**

- 分钟级业务因子**不要**自己用 `getPrevTick` 重算 1min 聚合，而是依赖 nonfactor 的列表字段；
- 使用最近一个时间点的数据时，采用 `xxx_list[-1]`；
- 如需窗口内多个点的数据，可以用切片或循环访问 `xxx_list[-n:]`。

""" + PROMPT_FACTOR_L3_PY_DEMO_SAMPLE + """
""" + PROMPT_FACTOR_L3_PY_MIN_1S + """

2. 已有 nonfactor 能力：
下面提供了当前可用的 NonFactor 源码详情。请仔细阅读这些源码，确认可用的列表字段名（如 `trade_buy_money_list`）和数据含义。
**不要凭空猜测字段名，必须以提供的源码为准。**

{nonfactor_infos}

3. 你在写业务因子时，不要重新计算这些非因子逻辑，而是：
- 分钟级业务因子不要自己用 getPrevTick 重算 1min 聚合，而是依赖 nonfactor 的列表字段；
- 先根据用户的文字描述，决定应该依赖哪些 nonfactor（例如交易动量因子往往用 FactorSecTradeAgg）。
- 在 __init__ 中通过 self.get_factor_instance("NonFactorName") 获取实例。
- 在 calculate 中，通过 nonfactor 的列表属性读取最近一分钟或最近 N 分钟的数据进行计算。
- 在计算一些分钟频因子时，可能会涉及到分钟频秒级因子计算，这时你需要注意不同nonfactor的回看窗口时间，有的是以秒为单位，有的是以分钟为单位

# 【三、你的工作流程】
你需要遵循以下步骤生成代码：

### 1. **解析需求**


-用1-3句自然语言总结：这个因子想刻画的核心现象 / 行为是什么？用于捕捉什么交易特征？

-数据粒度（从下列选项中选择并说明理由）

 -tick：逐笔成交 / 委托数据

 -1s 采样：按秒重采样后的数据

 -1min 采样 / bar：按分钟聚合或采样数据

 -其他（请说明）

 --输出示例：数据粒度：tick，原因：需要利用逐笔成交方向与微结构信息。

-因子类型（从下列类别中选择，可多选）

 -成交行为（如动量、方向性、成交节奏）

 -订单流（如买卖盘不平衡、主动买/卖力度）

 -盘口结构（如价差、深度分布、盘口形状、挂单撤单）

 -波动 / 风险（如短期波动率、极端波动）

 -其他（请说明）

 --输出示例：因子类型：成交行为 + 订单流，原因：关注短期价格动量与买卖力量。

-主要依赖指标（从下列指标中选择并补充说明）

 -成交类：成交金额、成交量、成交笔数、买卖方向

 -委托类：挂单数量、挂单金额、委托笔数、撤单数量

 -盘口类：买一/卖一价差、前 N 档深度、盘口不平衡

 -价格类：最高价、最低价、收盘价、中间价等

 -其他自定义指标

 --输出示例：主要依赖指标：秒级最后一笔成交价、成交量、买卖盘不平衡度。

-主要计算逻辑（从下列运算类型中选择，可多选）

 -统计类：平均值、最大值、最小值、标准差、分位数

 -比值/差值类：比值、差值、比例变化、收益率

 -计数类：计数、频次、占比

 -结构类：连续区间长度（如连续上涨秒数）、斜率、趋势强度

 -其他（请说明）

 --输出示例：主要计算逻辑：在滚动窗口内统计“连续上涨秒数”的最大值（连续区间长度）。

-需求解析完成后，根据需求中提到的变量去nonfactor中查找，并在初始化方法中调用含有这些变量的nonfactor实例


- 如果用户明确说明“采样 1min 因子”或提到 `FactorSecXXX`，或者没有明确提到要从逐笔数据重头开始计算，优先走 nonfactor 路径。

### 2. **选择数据路径与 nonfactor 组合**

- 若为逐笔因子：
  - 使用 `getPrevTick` / `getPrevNTick` / `getPrevSecTrade` 等接口取数；
  - 遵循 `ActivePriceVolume` 的写法风格。
- 若为采样 1min 因子：
  - 在 `FactorSecOrderBook / FactorSecTradeAgg / FactorSecOrderAgg / FactorSecTradeAgg2/ NfBaseSec/ FactorLevel` 中选择 1~2 个最合适的 nonfactor；
  - 仔细阅读上文提供的 NonFactor 源码，确认字段名和含义；
  - 不要在因子内部重复实现采样逻辑。

### 3. **设计具体计算逻辑**

- 明确每个输入量：
  - 成交行为类因子：从 `FactorSecTradeAgg` 等 nonfactor 的列表中取最近一个或最近 N 个元素，计算买卖方向强度、动量、反转等；
  - 订单流类因子：使用 `FactorSecOrderAgg` 中的买卖数量/笔数等数据，构造买卖不平衡、净流量等；
  - 盘口结构类因子：使用 `FactorSecOrderBook` 的价量序列构造价差、区间、波动、挂单集中度等；
  - 每秒一档盘口类因子：使用'NfBaseSec'的每秒盘口一档数据可以聚合每分钟一档数据;
  - 每秒前五档盘口类因子：使用‘FactorLevel’的每秒盘口前五档数据可以聚合每分钟前五档数据;
- 注意边界：
  - 当列表长度不足以支撑当前计算时，应返回 `0.0` 或一个合理的默认值；
  - 当存在除法时，分母为 0 或接近 0 时要避免除零错误，可以返回 `0.0` 或做平滑处理（例如加 1 或加 EPSILON）。

### 4. **生成最终因子代码**
生成一个完整、可运行的 Python 因子文件内容，包含：

- 必要的 import：

  ```python
  import numpy as np
  from L3FactorFrame.FactorBase import FactorBase
from domain.codegen.view import CodeGenView
from domain.codegen.l3_py_agent import invoke_l3_agent
  ```

- 因子类定义 `class FactorXxx(FactorBase)`；这个类名称，应该和用户提供的因子名称一模一样;

- __init__ 实现：调用 super().__init__ + 通过 self.get_factor_instance 获取所需 nonfactor
- calculate 实现：基于 nonfactor 的列表属性，完成一次因子值计算，并用 self.addFactorValue 写入结果。


  
### 5. **自检（必须）**
在给出最终答案前，你必须使用工具自检代码质量：

- 调用工具 `l3_syntax_check` 检查：
  - 代码语法是否正确；
  - 是否存在继承 `FactorBase` 的类；
  - 因子类是否和用户提供的因子名称一样
  - 是否实现了 `calculate` 方法。
- 至少调用一次 l3_mock_run，在 stub 的 L3 环境下执行 calculate，看是否能正常运行并调用 addFactorValue。
- 如果工具返回错误，请根据错误信息修正代码，再重新进行自检，通过后再给出最终答案。

# 【四、输出要求】
- 最终回复时，只输出完整的 Python 源代码：
- 不要包含任何 Markdown 代码块标记（不要写 ```python）。
- **不要**输出解释文字、分析过程或工具调用结果，只要源代码本身。
- 代码必须是可以直接保存为 `FactorXxx.py` 并在 L3FactorFrame 环境中运行的内容。

请严格遵守以上所有规范，特别是：
- 因子类结构与 FactorBase 规范；
- 对 nonfactor 字段名和含义的正确使用；
- 对 L3 逐笔接口和采样 1min nonfactor 的区分与选择；
- 使用 self.addFactorValue 写入结果。
"""

_L3_AGENT: Optional[Any] = None


def build_l3_codegen_agent():
    """Build or reuse cached L3 ReAct agent."""
    global _L3_AGENT
    if _L3_AGENT is not None:
        return _L3_AGENT

    tools = [
        l3_syntax_check,
        l3_mock_run,
    ]

    _L3_AGENT = create_agent(tools=tools)
    return _L3_AGENT


def build_l3_py_user_message(view: CodeGenView) -> HumanMessage:
    sem = view.check_semantics
    last_error = sem.last_error if sem else ""
    if sem and sem.reason and not last_error:
        last_error = "; ".join(sem.reason)
    dryrun = view.dryrun_result

    user_content = (
        f"因子类名: {view.factor_name}\n"
        f"因子需求描述: {view.user_spec or ''}\n")
    if view.factor_code:
        user_content+=f"因子代码: {view.factor_code}\n"
    if last_error:
        user_content += f"\n[上一轮错误摘要]\n{last_error[:2000]}\n"
    if dryrun and (dryrun.stdout or dryrun.stderr):
        user_content += "\n[上一轮运行信息]\n"
        if dryrun.stdout:
            user_content += f"stdout:\n{str(dryrun.stdout)[:2000]}\n"
        if dryrun.stderr:
            user_content += f"stderr:\n{str(dryrun.stderr)[:2000]}\n"

    return HumanMessage(content=user_content)


def get_formatted_nonfactor_info_py() -> str:
    """Python NonFactor字段与源码摘要。"""
    lines = []
    for name, meta in PY_NONFACTOR_META.items():
        lines.append(f"\n--- {name} ---")
        lines.append(meta.desc)
        for field, desc in meta.fields.items():
            lines.append(f"- {field}: {desc}")

    lines = lines+["\n【Python NonFactors 源码】"]
    for name, path in PY_NONFACTOR_PATH.items():
        lines.append(f"\n--- {name} ---")
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines.append(f.read())
        except Exception as e:
            lines.append(f"Error reading source: {e}")
    return "\n".join(lines)



def invoke_l3_agent(view: CodeGenView) -> str:
    """使用 L3 专用 ReAct agent 生成 FactorBase 规范代码。"""
    agent = build_l3_codegen_agent()
    if agent is None:
        # 简单回退：生成一个占位因子，避免空结果影响流程
        return (
            "from L3FactorFrame.FactorBase import FactorBase\n\n"
            f"class {view.factor_name}(FactorBase):\n"
            "    def __init__(self, config, factorManager, marketDataManager):\n"
            "        super().__init__(config, factorManager, marketDataManager)\n"
            "    def calculate(self):\n"
            "        self.addFactorValue(0.0)\n"
        )

    formatted_prompt = PROMPT_FACTOR_L3_PY.replace(
        "{nonfactor_infos}", get_formatted_nonfactor_info_py()
    )
    sys = SystemMessage(content=formatted_prompt)
    user = build_l3_py_user_message(view)

    try:
        out = agent.invoke({"messages": [sys, user]})
        msgs = out.get("messages") or []
        txt = _extract_last_assistant_content(msgs)
        return _unwrap_agent_code(txt).strip()
    except Exception as e:
        return f"ERROR: Agent invoke failed: {e}\nclass {view.factor_name}(FactorBase):\n    pass"


if __name__ == "__main__":
    print(PROMPT_FACTOR_L3_PY)
    """
    L3 因子代码生成 Agent 调用示例
    """
    # 1. 构造一个 CodeGenView 实例s
    view = CodeGenView(
        factor_name="FactorBelow2Amt",
        user_spec="采样1min因子:对过去3600s进行采样，计算从当前价格的98%,到当前价格的成交金额，只计算最后一次，注意这个价格取分钟频的秒级数据",
        factor_code=None,  # 首次调用可不传
        dryrun_result=None,
        check_semantics=None,
    )
    start_time = time.time()
    # 2. 调用 Agent 生成因子源码
    factor_py_source = invoke_l3_agent(view)

    # 3. 保存到文件
    with open(f"{view.factor_name}.py", "w", encoding="utf-8") as f:
        f.write(factor_py_source)
    end_time = time.time()
    print(f"生成时间: {end_time - start_time:.2f} 秒")
    print(f"生成完毕，文件已保存为{view.factor_name}.py")
