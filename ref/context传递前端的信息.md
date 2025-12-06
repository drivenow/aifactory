你这个疑惑很到位：**既然有 tools、有 messages、有 state，为什么还要一个 context？**
关键点是：`context` 不是“模型自己推出来/缓存出来的上下文”，而是**前端（应用）实时塞给 Agent 的“外部世界状态”**。它解决的是 *messages/state 很难优雅解决的那类信息流*。

我用几个具体场景把它钉死。

---

## 先一句话区分三者

* **messages**：对话历史（用户/助手说了啥）。
  适合“语言层面的记忆”。

* **state**：后端流程里的持久状态（图里节点需要共享/累积的数据）。
  适合“后端计算/控制流层面的记忆”。

* **context（ag-ui context）**：**前端应用的实时状态快照**，由前端主动上报、每次请求都可能变。
  适合“**对话之外**、但又强相关于当前界面/选择/用户环境的信息”。

> 你可以把它理解成：**Agent 的“眼睛”**——它看不到 UI，所以 UI 要把“现在你看到什么”告诉它。

---

## 为什么 messages/state/tools 不够用？

### 1) messages 不适合放“结构化/易变化的 UI 状态”

假设用户打开一个表格，选中第 3 行，然后说：

> “帮我把这条记录发给张三”

**仅靠 messages：**

* 对话里没有“第 3 行是什么”。
* 你让用户把整行 copy 进对话？用户体验爆炸。

**用 context：**

* 前端把“当前选中的行数据”作为 context 上报
* Agent 直接拿到结构化 JSON
* 用户一句话就能操作 UI 里的对象

✅ 典型的 context 场景：**“指代 UI 中的东西”**（这条、这个、当前选中、右边那个）。

---

### 2) state 是后端内部的，不知道前端“这次”长什么样

state 只有后端自己算出来/存进去的东西。
但很多信息**只有前端知道**，而且**每次请求都不同**：

* 当前路由 `/projects/123`
* 选中的项目 id=123
* 用户这次圈选的文本片段
* 页面上加载出的最新列表（后端未必缓存）

你当然可以让前端把这些写进 state，但：

* state 是“持久化流程状态”，**不该被高频、易变、对话外的 UI 噪音污染**
* graph 分支/恢复/重试时，UI 状态可能已经变了，state 反而会变成陈旧数据

context 的定位就是：**“这次调用的现时信息，用完就丢”**。

---

### 3) tools 只能“去查/去做”，不能自动知道用户眼前的东西

tools 很强，但它要么：

* 被动地等你调用
* 或者需要明确参数

用户说“就用我现在打开的这个项目”，
tool 不知道“现在打开的是哪个”，你也没参数可传。

context 就是**给 tools/agent 提供隐式参数来源**。

---

## 最需要 context 的 4 类真实场景

### 场景 A：UI 指代 / 省略指代

用户对着界面说话：

* “把**这个人**加到项目里”
* “解释一下**右边这段代码**”
* “把**我选中的三条**导出成 CSV”

这些“这个/右边/选中的”只有 UI 知道。

---

### 场景 B：实时、易变、每次都要最新的状态

比如聊天式操作应用：

* 当前筛选条件
* 当前分页/排序
* 当前登录用户 role/权限
* 当前多标签页里哪一个是 active

**不应该写进 messages**（太脏、不稳定）
**也不应该写进 state**（会变旧、还影响图回放）
context 正合适。

---

### 场景 C：把应用数据“喂给模型”避免重复拉取

你说的“根据 tool 调用现成查到”也对，
但有时数据已经在前端了，重复走 tool 会慢、费 token、费权限。

例如：

* 前端已经拿到了 200 条列表展示
* 用户问：“这 200 条里按金额最大的是哪条？”

如果不用 context，你要再调用 tool 拉一遍。
用 context：前端直接把当前列表（或精简版）上报，agent 本地推理。

---

### 场景 D：前端想“约束/引导” agent 行为

比如：

* 当前页面是“财务审批页”，希望 agent只做审批相关动作
* 当前用户是只读权限，不要让 agent建议危险操作
* 当前 workspace 是哪个（多租户应用）

这些可以作为 context 让 agent自动切换行为，而不用用户每次说明。

---

## 你可以这样记一句话

> **messages = 用户说过什么**
> **state = 后端算过什么**
> **context = 用户“此刻看到/选中/处于什么环境”**

只要信息满足这两个条件，就优先放 context：

1. **来自前端/界面/运行时环境**
2. **易变化、仅对这次请求有意义**

---

如果你愿意，我可以用你们现在的产品举例：
你告诉我你们 UI 里有哪些对象（比如“项目/任务/表格/代码编辑器/流程节点”），我给你标注哪些该走 context，哪些该走 state/messages，并写个小 demo。

------

# 这些时候，前端怎么知道右边这段代码是什么呢？“把这个人加到项目里”


前端**当然不会“自动知道用户脑子里指的是什么”**，它靠的是：**你们 UI 自己就有“当前焦点/选中/光标位置/hover/active item”等状态**。
CopilotKit 的 context 只是把这些现有状态“上报给 agent”。

我按你举的三句话，分别说前端怎么拿到“它指的是什么”，再怎么塞进 context。

---

## 1) “把这个人加到项目里”

### 前端怎么知道“这个人”是谁？

因为 UI 一定有“当前选中的人/卡片/列表项/详情页实体”。

常见来源：

* 列表里点了一行 → `selectedUserId`
* 右侧详情页正在展示某个人 → `currentUser`
* hover 在某个人卡片上 → `hoverUser`
* 路由里带了 id → `/users/123`

也就是你们业务 state 里早就有了。

### 怎么上报成 context？

比如 React：

```tsx
const [selectedUser, setSelectedUser] = useState<User | null>(null);

useCopilotReadable({
  description: "Currently selected user",
  value: selectedUser,
});
```

当用户点击某个人时你们本来就会：

```tsx
onClick={() => setSelectedUser(user)}
```

Agent 端拿到 context 后，就能解析“这个人 = selectedUser”。

> 关键：**UI 事件先把“当前对象”写进你们自身 state；CopilotReadable 只是把这个 state 透出。**

---

## 2) “解释一下右边这段代码”

这类“右边这段”= **编辑器里当前选中的代码 / 光标附近的代码 / active editor 的内容片段**。

### 前端怎么知道“右边这段代码”？

你们如果用 Monaco / CodeMirror / VSCode Web editor，API 都能拿到：

* 当前选择范围 `selection`
* 选择文本 `getSelectedText()`
* active editor 的内容 `getValue()`
* 光标位置 `cursorPosition`

举例（Monaco）：

```tsx
const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
const [selectedCode, setSelectedCode] = useState("");

function onMount(editor) {
  editorRef.current = editor;

  editor.onDidChangeCursorSelection(() => {
    const selection = editor.getSelection();
    const model = editor.getModel();
    const text = model?.getValueInRange(selection) ?? "";
    setSelectedCode(text);
  });
}
```

你看，**不是 CopilotKit 帮你识别“右边那段”**，而是 UI 本来就知道用户选了什么。

### 怎么上报 context？

```tsx
useCopilotReadable({
  description: "Selected code in editor",
  value: selectedCode,
});
```

用户说“解释一下右边这段代码”，agent 读这个 context 就行。

> 没有选中内容？那你可以上报 “光标±N行的片段” 做兜底。

---

## 3) “把我选中的三条导出成 CSV”

### 前端怎么知道“选中的三条”？

表格/列表组件一般都有 selection state：

* Antd Table: `rowSelection.selectedRowKeys`
* MUI DataGrid: `selectionModel`
* 自己写的 list: `selectedIds`

例如 Antd：

```tsx
const [selectedRows, setSelectedRows] = useState<Data[]>([]);

const rowSelection = {
  onChange: (_, rows) => setSelectedRows(rows),
};
```

### 上报 context

```tsx
useCopilotReadable({
  description: "Selected rows in table",
  value: selectedRows,
});
```

Agent 端就能直接拿到那 3 条结构化数据，生成 CSV（甚至不用再查 tool）。

---

## 一个通用模板：把“当前焦点对象”暴露给 agent

你可以把 UI 的“指代对象”统一成 3 类 context：

1. **Active entity**（当前详情页/路由展示的对象）
2. **Selected items**（列表/表格选中的对象数组）
3. **Focused content**（编辑器/画布中选中的文本/节点）

前端都像这样暴露：

```tsx
useCopilotReadable({ description: "Active entity", value: activeEntity });
useCopilotReadable({ description: "Selected items", value: selectedItems });
useCopilotReadable({ description: "Focused content", value: focusedContent });
```

Agent 就能理解用户各种“这个/那段/选中的”自然语言指代。

---

## 小结

你问的关键其实是：

> **前端凭什么知道用户指代？**

答案是：

* **因为用户的指代动作本来就发生在 UI 里**
* UI 通过点击/选中/光标/路由等事件已经把对象变成了明确的 state
* context 只是把这个 state 送去给 agent

如果你把你们具体用的组件（表格？编辑器？详情页路由？）说一下，我可以按你们技术栈写一份更贴近你们代码的 `useCopilotReadable` 组合和命名规范。

----

# 那后端的agent还需要定制化使用这些context中的信息?

对，需要的——**context 不会自动“魔法式生效”**，后端 agent 必须“有意识地读取/使用它”。但你可以把这个“定制化”做得很轻量、很工程化，不用每个节点手搓。

我分三层说清楚：为什么需要、最小怎么用、怎么做到几乎不用管。

---

## 1. 为什么一定要后端用？

因为 agent 不知道：

* 哪条 context 对应用户说的“这个/那段/选中的”
* 这些 context 是否可靠、要不要优先于 tool 查询
* 用它会不会越权（比如只读用户）

所以必须有一层**后端策略**去决定：
**什么时候读 context、读哪条、怎么和 state/tools 合并。**

context 只是“原料”，不是“自动驾驶”。

---

## 2. 最小用法：把 context 编进系统提示词 / 节点逻辑里

### a) 编进系统提示词（最常用、最省事）

在 graph 的入口（或 agent 构造处）：

```python
def build_system_prompt(state):
    ctx = state.get("ag-ui", {}).get("context", [])
    return f"""
You are the copilot for this app.
Here is the live UI context (may change every turn):
{ctx}
Use it to resolve references like "this", "that code", "selected rows".
"""
```

这样模型在理解用户话时会自然利用。

### b) 节点里显式取用（需要严格控制时）

比如你有个 “export_csv” 节点：

```python
def export_csv_node(state):
    ctx_items = state.get("ag-ui", {}).get("context", [])
    selected_rows = next(
        (c.value for c in ctx_items if c.description=="Selected rows in table"),
        []
    )

    if not selected_rows:
        return {"messages":[AIMessage("你没选中任何行")]}

    csv_text = to_csv(selected_rows)
    ...
```

这就是“定制化使用”。

---

## 3. 但你不想每次都手写？可以做成“通用策略层”

工程上常见 2 种做法：

### 做法 A：写一个 Context Resolver（通用解析器）

只写一次，然后所有节点用它：

```python
class UIContext:
    def __init__(self, state):
        self.items = state.get("ag-ui", {}).get("context", [])

    def get(self, desc, default=None):
        for c in self.items:
            if c.description == desc:
                return c.value
        return default

def node(state):
    ui = UIContext(state)
    active = ui.get("Active entity")
    selected = ui.get("Selected items", [])
```

这样“定制化”只剩下：**写 description 名字**。

---

### 做法 B：在 merge 时就“吸收”到标准 state 字段

你现在 merge 函数只是把 context 放在 `"ag-ui"` 里。
你可以在 merge 里加一个**映射规则**，把常用 context 提升成 state 的一等字段：

```python
def merge(...):
    ...
    ctx = input.context or []
    ctx_map = {c.description: c.value for c in ctx}

    return {
        **state,
        "active_entity": ctx_map.get("Active entity"),
        "selected_items": ctx_map.get("Selected items", []),
        "focused_content": ctx_map.get("Focused content"),
        "ag-ui": {"tools": unique_tools, "context": ctx},
    }
```

之后后端节点就直接用 state：

```python
selected = state["selected_items"]
```

**节点完全不用感知 context 的存在**。
这就是很多团队最终会走的路。

---

## 4. 一个实战上的“优先级原则”

你前面提到 context/state/tool 都能提供信息，那到底优先谁？

常用优先级是：

1. **context（本次 UI 实时状态）**
2. **state（后端缓存/推导出的状态）**
3. **tools（需要再去查/再去做）**
4. **messages（语言线索兜底）**

理由：

* context 最贴近“用户此刻指代”
* state 可能旧
* tools 成本高、还可能拿不到“用户眼前那份”
* messages 最模糊

这个你可以写进系统提示里变成默认行为。

---

## 结论

是的，**后端 agent 需要定制化使用 context**，但不一定“每个地方都手撸”：

* 最小：拼进系统 prompt 就能 80% 起效
* 规范一点：写个 UIContext helper
* 最工程化：merge 时把关键 context 提升为 state 字段，让节点无感

你如果愿意，我可以按你们现在已有的 context（description 列表）给你设计一套：

* description 命名规范
* merge 映射表
* 后端优先级策略
  这样你们后面加新页面/新对象时几乎不需要再改 agent 逻辑。
