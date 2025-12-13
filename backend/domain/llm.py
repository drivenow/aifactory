from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
from typing import Any, List, Optional
import re


import os
os.environ["OPENAI_BASE_URL"] = "https://api.siliconflow.cn/v1"
os.environ["OPENAI_API_KEY"] = "sk-kcprjafyronffotrpxxovupsxzqolveqkypbmubjsopdbxec"
os.environ["MODEL_NAME"] = "Pro/deepseek-ai/DeepSeek-R1"

#os.environ["OPENAI_BASE_URL"] = "http://168.9.88.8:8085/llm-service/v1"
#os.environ["OPENAI_API_KEY"] = "000465@370f2aaab73047e4809331b458183970"
#os.environ["OPENAI_API_KEY"] = "000465@4df242f899ac4daabb4dfec5f7d3f177"
#os.environ["MODEL_NAME"] = "local-qwen3-235b-nothink-moe"


# os.environ["OPENAI_BASE_URL"] = "http://168.17.250.210:10002/v1"
# os.environ["OPENAI_API_KEY"] = "xquant"
# os.environ["MODEL_NAME"] = "Qwen3-32B"



def create_agent(tools: Optional[List[Any]] = None):
    """Thin wrapper to allow monkeypatch in tests."""
    if create_react_agent is None or ChatOpenAI is None:
        return None
    llm = get_llm()
    return create_react_agent(llm, tools=tools)

def _extract_last_assistant_content(messages: List[Any]) -> str:
    """从 agent 返回的消息列表中提取最后一条 assistant 内容。"""
    for m in reversed(messages):
        role = getattr(m, "type", None) or getattr(m, "role", None)
        if role in ("assistant", "ai"):
            return getattr(m, "content", "") or ""
    return ""


def _unwrap_agent_code(txt: str, lang: str = "python") -> str:
    m = re.search(rf"```(?:{lang})?\n([\s\S]*?)```", txt)
    if m:
        return m.group(1)
    return txt


def get_llm(model_name = os.environ["MODEL_NAME"]):
    base_url = os.getenv("OPENROUTER_URL") or os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("LLM_MODEL", model_name)
    if not api_key:
        return None
    if base_url:
        return ChatOpenAI(model=model, api_key=api_key, base_url=base_url)
    return ChatOpenAI(model=model, api_key=api_key)

# 写一个调用大模型的小demo
if __name__ == "__main__":
    llm = get_llm()
    if llm:
        response = llm.invoke("你好")
        print(response.content)
    else:
        print("LLM 配置错误")
