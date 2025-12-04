# codegen 模块导航

- `view.py`：把 `FactorAgentState` 规整成 `CodeGenView`，统一字段、默认值、容错。
- `generator.py`：按 `code_mode` 生成代码；Pandas 用模板渲染，L3 调用 agent。
- Agent 现位于 `backend/graph/agent.py`，可被各 domain 复用；必要时可替换为自定义实现。
- `tools/`：L3 专用工具（语法检查、mock 运行、nonfactor 元数据）。
- `runner.py`：运行或 mock 运行因子，保证输出字段一致。
- `validator.py`：语义检查/结果标准化，输出布尔 + detail。

调用顺序建议：collect_spec → generator.generate_factor_code_from_spec → runner.run_factor → validator.is_semantic_check_ok（失败态附带 reason/last_error）。替换某一环时，只要保持输入输出契约即可。
