import os
from typing import Optional
from langchain_openai import ChatOpenAI

RETRY_MAX = 3

# base_url = "https://api.deepseek.com"
# api_key = "sk-eb7b2844c60a4c88918a325417ac81f7"
# model_name = "deepseek-chat"  # deepseek-reasoner

os.environ["OPENAI_BASE_URL"] = "https://api.siliconflow.cn/v1"
os.environ["OPENAI_API_KEY"] = "sk-kcprjafyronffotrpxxovupsxzqolveqkypbmubjsopdbxec"

def get_llm(model_name = "Pro/deepseek-ai/DeepSeek-R1"):
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