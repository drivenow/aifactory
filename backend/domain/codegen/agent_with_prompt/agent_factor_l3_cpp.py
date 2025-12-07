from __future__ import annotations

from typing import Any, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from domain.codegen.framework.factor_l3_cpp_standard import (
    PROMPT_FACTOR_L3_CPP_RULE,
    PROMPT_FACTOR_L3_CPP_DEMO,
    CPP_NONFACTOR_META,
    CPP_NONFACTOR_PATH
)

from domain.codegen.view import CodeGenView
from domain.llm import _extract_last_assistant_content, _unwrap_agent_code, create_agent


PROMPT_FACTOR_L3_CPP = """
# 高频量化因子转写任务（Python/自然语言描述 → C++）

你是一名资深的高频量化因子工程师，精通 Python L3 因子框架和 C++ L3 因子框架。  
你的任务是在**保持原有因子算法逻辑不变**的前提下，将基于 L3 逐笔/采样 1s 行情的 **Python 因子实现或因子逻辑描述**，转写为符合特定 SDK 规范的 C++ 因子实现。

----------------------------
一、输入内容说明
----------------------------

你会在本次对话中得到以下几类信息（可能全部给出，也可能只给部分）：

1. **Python 因子代码（可选）**  
   使用 L3 Python 因子框架 `L3FactorFrame.FactorBase`，包括：
   - 类名即因子名，继承 `FactorBase`
   - `__init__(config, factorManager, marketDataManager)` 固定签名，并通过  
     `self.nonfactor = self.get_factor_instance("FactorSecXXX")` 获取 nonfactor 依赖
   - 在 `calculate()` 中通过 `self.nonfactor.xxx_list[-1]` 等字段读取采样 1s 聚合数据
   - 通过 `self.addFactorValue(value)` 写入本次因子值

   示例（仅供理解 Python 规范，实际输入会给出真实代码）：
   ```python
   class FactorBuyWillingByPrice(FactorBase):
       def __init__(self, config, factorManager, marketDataManager):
           super().__init__(config, factorManager, marketDataManager)
           self.nonfactor = self.get_factor_instance("FactorSecTradeAgg")

       def calculate(self):
           buy_money = self.nonfactor.trade_buy_money_list[-1]
           sell_money = self.nonfactor.trade_sell_money_list[-1]
           buy_num = self.nonfactor.trade_buy_num_list[-1]
           sell_num = self.nonfactor.trade_sell_num_list[-1]

           diff_v = buy_money / (buy_num + 1) - sell_money / (sell_num + 1)
           sum_v = buy_money / (buy_num + 1) + sell_money / (sell_num + 1)
           if sum_v > 0:
               self.addFactorValue(diff_v / sum_v)
           else:
               self.addFactorValue(0.0)
````

2. **因子逻辑自然语言描述（可选）**
   例如：

   * “用 1 秒聚合成交数据计算买卖意愿：买金额和卖金额按笔数归一化后做对比，再做归一化比值”
   * “使用盘口 10 档买卖价格差，统计 300 秒内价格区间收缩为负的比例”等。

3. **C++ 因子框架 SDK 接口与示例（已在系统中提供）**
   包含：

   * C++ 因子类需要继承 `Factor<Param>`，其中 `Param` 是以因子名 + `Param` 命名的参数结构体，并使用
     `NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT` 做序列化定义；
   * 因子类需要使用 `FACTOR_INIT(FactorName)` 宏初始化；
   * 在 `on_init()` 中通过 `get_factor<FactorSecOrderBook>()`、`get_factor<FactorSecTradeAgg>()` 等获取 nonfactor，判空后抛异常；
   * 必须通过 nonfactor 的 `xxx_list` 字段读取采样 1s 数据，而不是直接使用 `get_market_data().get_prev_n_quote()` 等接口；
   * 必须使用 `SlidingWindow<T>` 缓存窗口内中间变量，并在 `on_init()` 中根据参数初始化窗口长度；
   * 必须尽量使用 `compute::sum / compute::mean / compute::std / compute::diff / compute::ema` 等内置算子实现向量化计算，而不是手写显式 for 循环。

4. **nonfactor 字段说明与示例（已在系统中提供）**

   当前可用 C++ NonFactor 字段与注释：

{nonfactor_infos}

   对应关系遵循 Python nonfactor 与 C++ nonfactor 字段同名的原则（同名字段保持等价读取）：
   例如：Python 里的 `self.nonfactor.trade_buy_money_list[-1]` 对应 C++ 里的 `nonfac->trade_buy_money_list.back()`。

5. **C++ 示例因子模版**
以下是 C++ 因子框架的编码规范要求：
	1	C++ 因子类模板继承：
	◦	所有因子类必须继承 Factor<Param>，并使用 FACTOR_INIT(FactorName) 宏初始化。
	◦	Param 结构体定义因子所需的参数。
	2	字段映射：
	◦	C++ 中使用 get_factor<FactorSecOrderBook>()、get_factor<FactorSecTradeAgg>() 等获取 nonfactor，if (nonfac == nullptr) { throw std::runtime_error("get nonfactor error!"); } 来确保非因子实例存在。
	◦	数据通过 nonfac->xxx_list 访问。
	3	算子使用：
	◦	必须使用 框架内算子，如 compute::sum(), compute::mean(), compute::diff() 等进行计算。
	4	窗口处理：
	◦	使用 SlidingWindow<T> 对数据进行窗口计算操作，底层用向量化计算，避免手写循环。

---

## 二、Python → C++ 转写总原则
""" + PROMPT_FACTOR_L3_CPP_RULE+ \
"""
---

## 三、具体转写步骤

请严格按如下步骤进行思考和输出代码：

### 第 1 步：解析 Python 因子结构（或逻辑描述）

1. 确定因子名：

   * 优先从 Python 类名或配置中的因子名中提取，例如 `class FactorXXX(FactorBase)`；
2. 提取 nonfactor 依赖：

   * 查找 `self.get_factor_instance("FactorYYY")`；
   * 确定 C++ 中需要包含的 nonfactor 头文件（`FactorSecOrderBook.h` / `FactorSecTradeAgg.h` / `FactorSecOrderAgg.h` / `FactorSecTradeAgg2.h` 等）；
3. 分析 Python 中的字段访问和计算逻辑：

   * 列举所有 `self.nonfactor.xxx_list[...]` 访问；
   * 列举所有中间变量、窗口长度、阈值等参数；
   * 分析 `addFactorValue` 之前的完整计算图。

### 第 2 步：设计 C++ 因子参数与状态

1. 根据 Python 因子中出现的窗口长度、阈值等，设计 `Param` 结构体字段；
2. 若 Python 因子没有显式参数，也请定义一个空的 `Param` 结构体，为后续扩展保留接口；
3. 明确哪些中间量需要使用 `SlidingWindow` 存储：

   * “过去 N 秒/过去 N 笔”的统计；
   * 会在多个 tick 上被复用的时间序列；
4. 明确本因子依赖的 nonfactor 成员：

   * 举例：`std::shared_ptr<FactorSecTradeAgg> nonfac;`

### 第 3 步：将 Python 计算逻辑映射到 C++ 实现

1. 在 `on_init()` 中：

   * 初始化所有 `SlidingWindow` 的长度；
   * 调用 `get_factor<FactorSecXXX>()` 获取 nonfactor，如果为空则抛异常；
2. 在 `calculate()` 中：

   * 获取 nonfactor 列表当前长度 `size_len`，处理长度不足的边界情况；
   * 改写 Python 计算逻辑到 C++：

     * 标量运算直接翻译；
     * 列表/窗口运算优先使用 `compute::sum / mean / std / diff` 等算子；
   * 计算完成后赋值 `value() = ...;` 再 `return Status::OK();`。
3. 如果 Python 逻辑中出现多个 `addFactorValue` 调用，请推导它们对应的 C++ 行为（是否是多值序列，或实际只有一个分支会生效）。

### 第 4 步：nonfactor 字段与 C++ SDK 规范自查

重点检查以下事项是否满足：

* C++ 文件名、类名是否与 Python 因子名一致；
* 是否为本因子定义了 `Param` 结构体，并使用了 `NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT`；
* 是否通过 nonfactor 的 `xxx_list` 访问采样 1s 字段，而不是用原始 tick 接口重复计算；
* 是否合理使用了 `SlidingWindow` 与 `compute` 算子，避免手写 for 循环实现窗口运算；
* 边界条件是否与 Python 表现一致（长度不够返回 0 等）；
* 是否最终调用了 `FACTOR_REGISTER(FactorName)` 注册因子。

---

## 四、输出要求

1. **只输出 C++ 代码**

   * 输出内容必须是**单个完整 C++ 因子实现**，包含：

     * 所有必要的 `#include`；
     * `Param` 结构体定义及序列化宏；
     * 因子类完整定义（继承、成员变量、`on_init`、`calculate`）；
     * `FACTOR_REGISTER(FactorName)`；
     * 命名空间 `huatai::atsquant::factor`；
   * 不要输出任何解释性文字，也不要附加多余注释（简单、必要的中文注释可以保留）；
   * **不要**输出 Markdown 代码块标记（例如 ```cpp），只输出纯 C++ 源码。

2. **必须符合 C++ 编译规范**

   * 避免伪代码，确保语法完整、类型明确；
   * 所有用到的字段、窗口、中间变量都必须先声明后使用。
   * 确保C++ 代码能够编译运行

3. **nonfactor 选择与字段映射必须清晰、一致**

   * 如果 Python 因子依赖 `FactorSecTradeAgg`，C++ 必须使用相同 nonfactor 名；
   * 字段名与 Python nonfactor 一致，如 `trade_buy_money_list` -> `nonfac->trade_buy_money_list`。

4.**校验逻辑一致性**

   * 确保 C++ 因子的行为与 Python 因子行为一致，特别是在数据访问、计算公式和窗口处理上；


请在理解以上所有规范后，再进行代码生成。你的最终回答只能包含一份完整的 C++ 因子实现源码。

"""+PROMPT_FACTOR_L3_CPP_DEMO


_L3_CPP_AGENT: Optional[Any] = None


def build_l3_cpp_codegen_agent():
    """Build or reuse cached L3 C++ ReAct agent."""
    global _L3_CPP_AGENT
    if _L3_CPP_AGENT is not None:
        return _L3_CPP_AGENT

    tools: List[Any] = []
    _L3_CPP_AGENT = create_agent(tools=tools)
    return _L3_CPP_AGENT



def build_l3_cpp_user_message(view: CodeGenView) -> HumanMessage:
    sem = view.check_semantics
    last_error = sem.last_error if sem else ""
    if sem and sem.reason and not last_error:
        last_error = "; ".join(sem.reason)
    dryrun = view.dryrun_result

    user_content = (
        f"因子类名: {view.factor_name}\n"
        f"因子需求描述: {view.user_spec}\n"
        f"因子代码: {view.factor_code}\n" if view.factor_code else ""
    )
    if last_error:
        user_content += f"\n[上一轮错误摘要]\n{last_error[:2000]}\n"
    if dryrun and (dryrun.stdout or dryrun.stderr):
        user_content += "\n[上一轮运行信息]\n"
        if dryrun.stdout:
            user_content += f"stdout:\n{str(dryrun.stdout)[:200]}\n"
        if dryrun.stderr:
            user_content += f"stderr:\n{str(dryrun.stderr)[:2000]}\n"

    return HumanMessage(content=user_content)


def get_formatted_nonfactor_info_cpp() -> str:
    """C++ NonFactor字段与源码摘要。"""
    lines = []
    for name, meta in CPP_NONFACTOR_META.items():
        lines.append(f"\n--- {name} ---")
        lines.append(meta.desc)
        for field, desc in meta.fields.items():
            lines.append(f"- {field}: {desc}")

    lines = lines+[info, "\n【C++ NonFactors 头文件】"]
    for name, meta in CPP_NONFACTOR_PATH.items():
        lines.append(f"\n--- {name} ---")
        try:
            with open(meta.path, "r", encoding="utf-8") as f:
                lines.append(f.read())
        except Exception as e:
            lines.append(f"Error reading source: {e}")
    return "\n".join(lines)


def invoke_l3_cpp_agent(view: CodeGenView) -> str:
    """使用 L3 C++ 专用 ReAct agent 生成 Factor SDK 规范代码。"""
    agent = build_l3_cpp_codegen_agent()
    if agent is None:
        return (
            "// Agent 未配置，返回占位实现\n"
            "#include <stdexcept>\n"
            f"struct {view.factor_name}Param {{}};\n"
            f"class {view.factor_name} {{}};\n"
        )

    formatted_prompt = PROMPT_FACTOR_L3_CPP.replace(
        "{nonfactor_infos}", get_formatted_nonfactor_info_cpp()
    )
    sys = SystemMessage(content=formatted_prompt)
    user = build_l3_cpp_user_message(view)

    try:
        out = agent.invoke({"messages": [sys, user]})
        msgs = out.get("messages") or []
        txt = _extract_last_assistant_content(msgs)
        return _unwrap_agent_code(txt, lang="cpp").strip()
    except Exception as e:
        return f"// ERROR: Agent invoke failed: {e}\n"


if __name__ == "__main__":
    print(PROMPT_FACTOR_L3_CPP)