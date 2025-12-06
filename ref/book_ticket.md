下面我先把这段代码里“系统 prompt”（SCHEDULE_SYSTEM、CONTACT_SYSTEM、CONFIRM_SYSTEM）拆开讲清楚它们各自想让 LLM 干什么、怎么约束输出；然后再按时间顺序把整个 agent 的完整流程走一遍，你就能把“prompt—structured output—state machine—interrupt”怎么配合起来吃透。

---

## 一、SCHEDULE_SYSTEM 在做什么（行为空间 + 决策规则）

这个 prompt 是 **“行程/航班选择阶段的操作手册”**。它的目标不是让模型自由聊天，而是：

1. **从用户话里抽取四个必需字段**

   * `trip_type`（one-way/roundtrip）
   * `destination`（目的地）
   * `date`（出发日期，可能是自然语言如 tomorrow）
   * `passengers`（人数）

2. **在字段齐了之后，展示固定的三档航班选项**
   A/B/C（文字格式严格固定）

3. **让模型用结构化输出（ScheduleAction）告诉代码：下一步要干啥**
   关键字段：

   * `human_input`: 是否要等用户回复
   * `message`: 要展示给用户的话
   * `selected_flight`: 用户选了 A/B/C 没
   * `ready_for_contact`: 是否可以进入下一阶段（contact）

### prompt 的“分支规则”可以理解为一个 if-else 树

你可以把它读成：

**规则 0：开局**

* 如果 `current_booking` 为空：

  * 打招呼
  * 提问“你想飞去哪？”
  * `human_input=true`

**规则 1：缺信息就补信息**

* 如果四个字段里缺任意一个：

  * 从用户话里尽量抽
  * 告诉用户你抽到啥
  * 问剩下缺什么
  * `human_input=true`

**规则 2：已经展示过航班就别再展示**

* 如果 `current_booking` 已经有 `selected_flight` 字段：

  * 不再重复显示 A/B/C
  * 看用户回复是不是 A/B/C

    * 是：抽出来，`ready_for_contact=true, human_input=false`
    * 不是：也直接 `ready_for_contact=true`（等 contact 阶段继续）

**规则 3：信息齐但还没选航班 → 必须展示航班**

* 四字段齐、但 `selected_flight` 为空：

  * message 必须包含固定格式的航班列表
  * `human_input=true`
  * **不能** `ready_for_contact=true`

**规则 4：检测到用户选了 A/B/C → 进入下一阶段**

* 如果用户 message 里像 “A / option B / flight c”：

  * 抽字母（大写）
  * `selected_flight=...`
  * `ready_for_contact=true`
  * `human_input=false`

### 这个 prompt 的本质

> 把 **“收集字段 → 展示选项 → 等用户选 → 进入下一阶段”** 的流程，写成非常硬的规则，让 LLM 输出稳定的 JSON。

---

## 二、CONTACT_SYSTEM 在做什么（乘客信息收集）

这是第二阶段（contact_agent）的系统 prompt。目标更简单：

1. **收集两项乘客信息**

   * `passenger_name`
   * `passenger_email`

2. **仍然用结构化输出（ContactAction）驱动流程**

   * `human_input`
   * `message`
   * `ready_for_confirmation`（是否可以去 confirm 阶段）

### 分支规则

**规则 0：缺 name 或 email 就问**

* 如果缺任意一项：

  * 尝试从用户话里抽
  * 但无论抽没抽到，只要还缺，就发固定提示语：
    “请给我全名和邮箱…”
  * `human_input=true, ready_for_confirmation=false`

**规则 1：两项都齐了就进入下一阶段**

* 如果 name/email 都有：

  * `ready_for_confirmation=true`
  * `human_input=false`
  * message 为空

### 本质

> 一个典型的二字段表单收集器。

---

## （补充）CONFIRM_SYSTEM 简述（确认 + 购物车逻辑）

你问“两段 prompt”，但要理解完整流程必须知道 confirm 的用意，所以我简要解释一下：

confirm 阶段的 prompt 目标是：

1. 给用户展示“订票摘要”，让用户确认 yes/no
2. 处理“加入购物车 / 再订一张 / 结束”的多轮意图

它要求模型输出 ConfirmAction：

* `action` = confirm / add_to_cart / complete / show_cart
* `human_input` 和 `message` 决定是否要等用户回

它的规则按照优先级写死：

* 当前 booking 不空 → 先让用户确认
* 用户确认后 → add_to_cart，并问要不要再订
* booking 为空且 cart 有东西 → 判断用户想再订还是结束
* 结束则 action=complete

---

## 三、完整 agent 流程（一步一步走）

下面按一次典型对话来走，你就能对应到代码。

### 0. 初始化

* `demo_graph = graph_builder.compile(memory)`
* entry point 是 `"schedule"`

state 初始大概是：

```python
{
  "messages": [HumanMessage("hi")],
  "route": "schedule",
  "enable_interrupt": False,
  "current_booking": {},
  "cart": [],
  "system_date": None
}
```

---

### 1. 进入 schedule_agent

做的事：

1. 确保 system_date 和 current_booking 有默认值

2. `route="schedule"`

3. 发事件 `schedule:start`

4. 组 prompt：

* `messages`（用户历史）
* `SystemMessage(SCHEDULE_SYSTEM.format(...))`

5. LLM structured 输出 `ScheduleAction`

6. 用 result 更新 state 的 booking 字段

7. **代码层做二次判断：**

* 是否四字段齐了
* 是否有 selected_flight

8. **根据 result 决定下一步：**

* 如果 ready_for_contact 或四字段齐且 flight 已选
  → `route="contact"`，不 interrupt

* 如果 human_input=true 且有 message
  → messages 变成 AIMessage(message)
  → `enable_interrupt=True`
  → route 仍为 schedule

* 否则（LLM 输出不合规）
  → 不 interrupt，route="schedule"
  → 让图再跑一轮 schedule（自旋）

---

### 2. route_or_interrupt 决定去哪

每个阶段后都会走这个路由器：

```python
if enable_interrupt:
    return "interrupt_node"
else:
    return route
```

* 如果刚才 schedule 说要等用户回
  → 跳到 interrupt_node
* 否则按 route（contact/confirm/schedule）走

---

### 3. interrupt_node（Human-in-the-loop）

1. 先把 `enable_interrupt=False` 避免重复

2. 发事件 `interrupt`

3. 把最后一条 AI message 当 prompt

4. `human_reply = interrupt(value=prompt)`

   * LangGraph 会在这里暂停，等前端/调用方把用户输入塞回来

5. 收到人类输入后：
   `state["messages"] = [HumanMessage(human_reply)]`

6. return → 路由回之前的 route（schedule/contact/confirm）

---

### 4. 进入 contact_agent

完全类似 schedule：

1. `route="contact"`
2. 发 `contact:start`
3. LLM structured 输出 ContactAction
4. 更新 passenger_name/email
5. 判断齐不齐
6. 齐了 → route="confirm"
   缺 → enable_interrupt=True → interrupt_node

---

### 5. 进入 confirm_agent

1. `route="confirm"`
2. 发 `confirm:start`
3. LLM structured 输出 ConfirmAction
4. 按 action 分支处理：

* `action="confirm"`

  * 发 booking summary
  * enable_interrupt=True（等用户 yes）

* `action="add_to_cart"`

  * 把 current_booking 加入 cart
  * 清空 current_booking
  * 然后问用户要不要再订 / 结束
  * enable_interrupt=True

* `action="complete"`

  * 确保 booking 入 cart
  * 发最终总结
  * route="END"

* 其它或不合规

  * 让 confirm 再跑一次

---

### 6. 结束

路由器看到 route="END"
→ 返回 `END` 节点
graph 完成

---

## 四、用一句话串起来

> 这个 agent 用 **三段结构化 LLM 表单节点（schedule/contact/confirm）** 逐步收集信息、控制流程；每段如果需要用户回复就把 `enable_interrupt=True`，路由到 `interrupt_node` 暂停等待；回填后再继续下一段；最后把订票加入 cart 并结束。

---

如果你想，我可以画一个“状态机 + interrupt”的简图（节点/边/状态字段变化），让你一眼看到每轮 state 的迁移。