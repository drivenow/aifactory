# /home/appadmin/anaconda3/lib/python3.11/site-packages/ag_ui_langgraph/agent.py
```python
    def langgraph_default_merge_state(self, state: State, messages: List[BaseMessage], input: RunAgentInput) -> State:
        if messages and isinstance(messages[0], SystemMessage):
            messages = messages[1:]

        existing_messages: List[LangGraphPlatformMessage] = state.get("messages", [])
        existing_message_ids = {msg.id for msg in existing_messages}

        new_messages = [msg for msg in messages if msg.id not in existing_message_ids]

        tools = input.tools or []
        tools_as_dicts = []
        if tools:
            for tool in tools:
                if hasattr(tool, "model_dump"):
                    tools_as_dicts.append(tool.model_dump())
                elif hasattr(tool, "dict"):
                    tools_as_dicts.append(tool.dict())
                else:
                    tools_as_dicts.append(tool)

        all_tools = [*state.get("tools", []), *tools_as_dicts]

        # Remove duplicates based on tool name
        seen_names = set()
        unique_tools = []
        for tool in all_tools:
            tool_name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", None)
            if tool_name and tool_name not in seen_names:
                seen_names.add(tool_name)
                unique_tools.append(tool)
            elif not tool_name:
                # Keep tools without names (shouldn't happen, but just in case)
                unique_tools.append(tool)

        return {
            **state,
            "messages": new_messages,
            "tools": unique_tools,
            "ag-ui": {
                "tools": unique_tools,
                "context": input.context or []
            }
        }
```
先不管 CopilotKit 官方怎么说，**就你这段 `langgraph_default_merge_state` 来看，它的“状态合并原则”可以概括成几条：**

---

## 1. 保留旧状态的其他字段，新值覆盖同名字段

```python
return {
    **state,          # 先把原来的 state 展开
    "messages": ...,
    "tools": ...,
    "ag-ui": ...
}
```

* 旧 `state` 里所有未知字段都原样保留（例如你自己塞进去的别的键）。
* 但 `messages` / `tools` / `ag-ui` 这三个键，用的是**这次合并之后的新值**覆盖旧值。

> 原则：**无损扩展 + 关键字段后者优先**。

---

## 2. SystemMessage 不参与合并

```python
if messages and isinstance(messages[0], SystemMessage):
    messages = messages[1:]
```

* 如果新消息列表第一个是 `SystemMessage`，直接丢掉。
* 也就是说，**系统提示词只用来指导模型，不会写入 CopilotKit 的状态**，避免污染前端对话历史。

> 原则：**只保留“真正对话消息”，不保存系统指令。**

---

## 3. 消息按 `id` 去重，只保留“新出现”的消息

```python
existing_messages: List[LangGraphPlatformMessage] = state.get("messages", [])
existing_message_ids = {msg.id for msg in existing_messages}

new_messages = [msg for msg in messages if msg.id not in existing_message_ids]
...
"messages": new_messages,
```

逻辑是：

1. 从旧状态中拿到已有的 `messages`，收集它们的 `id`。
2. 对这次传入的 `messages` 做过滤：**只保留那些 `id` 没出现在旧消息里的**。
3. 返回的新 `messages` 字段就是这些 `new_messages`。

> 理论原则本来是：**按消息 ID 做幂等去重：同一消息不会被重复写入**。
> 但是这里有个细节：`"messages": new_messages` 没把旧消息加回来，等于每次都只保留“这次新增的那一批”。如果你期望“累积对话历史”，这里应该是：
>
> ```python
> "messages": [*existing_messages, *new_messages]
> ```
>
> 否则前端看到的只会是最近一次合并的消息。

---

## 4. 工具列表按 name 去重，合并旧工具和新工具

```python
tools = input.tools or []
tools_as_dicts = []
for tool in tools:
    if hasattr(tool, "model_dump"):
        tools_as_dicts.append(tool.model_dump())
    elif hasattr(tool, "dict"):
        tools_as_dicts.append(tool.dict())
    else:
        tools_as_dicts.append(tool)

all_tools = [*state.get("tools", []), *tools_as_dicts]
```

这几步做的事：

1. 把这次传入的 `input.tools` 全部转成 dict（尽量调用 `model_dump` / `dict`），方便序列化和前端使用。
2. 和旧 state 里的 `tools` 合并成 `all_tools`：**旧的在前，新的在后**。

然后开始按 `name` 去重：

```python
seen_names = set()
unique_tools = []
for tool in all_tools:
    tool_name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", None)
    if tool_name and tool_name not in seen_names:
        seen_names.add(tool_name)
        unique_tools.append(tool)
    elif not tool_name:
        unique_tools.append(tool)
```

* 对有 `name` 的工具：**同名只保留第一次出现的那个**（由于旧工具在前，所以“旧的优先，新同名工具被忽略”）。
* 对没有 `name` 的工具：全部保留（不参与去重）。

最终：

```python
"tools": unique_tools,
"ag-ui": {
    "tools": unique_tools,
    "context": input.context or []
}
```

> 原则：
>
> * 工具列表是**累积的**：新工具会加进去，老的不会被清空。
> * 同名工具只保留一个，**旧的优先**，避免前端收到一堆重复工具定义。
> * UI 里用的工具列表和内部 `tools` 保持一致，同时用最新的 `input.context` 作为上下文。

---

## 5. `ag-ui` 采用“最新输入为准”

```python
"ag-ui": {
    "tools": unique_tools,
    "context": input.context or []
}
```

* UI 上显示的 `tools` 跟合并后的 `unique_tools` 一致。
* `context` 不继承旧的，而是直接用这次 `input.context`；如果没有就给空列表。

> 原则：**UI 上的 context 采用“最近一次调用”的值，避免脏数据**。

---

## 汇总一句话版

这个 `langgraph_default_merge_state` 的状态合并“原则”可以总结为：

1. **保留旧 state 的其他字段**，只更新 `messages` / `tools` / `ag-ui`。
2. **过滤掉 SystemMessage**，只把用户/助手等“真实对话”写入状态。
3. **消息按 `id` 去重**，只保留旧 state 没见过的消息（但当前实现没有把旧消息加回去，这是一个潜在问题）。
4. **工具按 `name` 去重并累积**：旧的优先，新同名忽略；没 name 的一律保留。
5. `ag-ui` 中的工具与内部工具同步，`context` 用**最新输入**覆盖旧值。

如果你说的“原则”是想知道“我如何自定义一个更合理的合并”，我可以直接帮你改一版，比如修一下 messages 的“只保留新增”问题，顺便加几个常见场景（多 agent 合并、分支状态合并）的写法。
