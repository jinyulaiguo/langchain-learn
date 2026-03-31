from langchain_openai import ChatOpenAI
from lang_series_project.core.config import settings

def get_deepseek_llm(temperature: float = 0.7):
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_api_base,
        max_tokens=4096,
        temperature=temperature
    )
