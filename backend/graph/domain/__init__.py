# backend/graph/domain/__init__.py
"""
领域逻辑模块（domain layer）

这里放与具体 LangGraph/Command 无关的纯业务函数：

- logic:    需求/描述提取相关
- codegen:  因子代码生成 + 沙盒 dryrun + 语义检查
- eval:     回测评价 & mock 入库
- review:   人审请求构造与人审结果解析
"""
