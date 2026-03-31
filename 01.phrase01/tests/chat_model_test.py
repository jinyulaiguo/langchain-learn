from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

llm = ChatOpenAI(model="deepseek-chat", api_key="sk-f5", base_url="https://api.deepseek.com/v1")
result = llm.invoke([HumanMessage(content="你好，请介绍你自己")])
print(result)

