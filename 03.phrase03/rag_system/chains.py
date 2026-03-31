import os
import sys
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LLM_MODEL

class Chains:
    """定义系统中基于不同路由路径的两个大语言模型问答执行链"""
    
    def __init__(self):
        # 初始化大模型 (默认使用 DeepSeek-chat，通过环境变量控制具体的 base_url/api_key)
        self.llm = ChatOpenAI(model=LLM_MODEL)
        self.output_parser = StrOutputParser()
        
        self.retrieval_chain = self._build_retrieval_chain()
        self.memory_chain = self._build_memory_chain()

    def _build_retrieval_chain(self):
        """基于检索文档片段的 Chain"""
        template = """你是一个基于文档的问答助手。根据以下检索到的文档片段回答用户问题。
如果文档片段不足以回答，请明确说明。

【检索到的文档片段】
{retrieved_context}

【用户问题】
{question}

请在回答末尾明确标注引用来源。
"""
        prompt = PromptTemplate(
            template=template,
            input_variables=["retrieved_context", "question"]
        )
        return prompt | self.llm | self.output_parser

    def _build_memory_chain(self):
        """基于历史对话记忆的 Chain"""
        template = """你是一个对话助手。根据以下对话历史回答用户问题。
如果历史中没有相关信息，请说明你无法基于对话历史回答。

【对话历史】
{chat_history}

【用户问题】
{question}
"""
        prompt = PromptTemplate(
            template=template,
            input_variables=["chat_history", "question"]
        )
        return prompt | self.llm | self.output_parser
    
    def run_retrieval_chain(self, question: str, retrieved_context: str) -> str:
        """执行检索链"""
        return self.retrieval_chain.invoke({
            "question": question,
            "retrieved_context": retrieved_context
        })

    def run_memory_chain(self, question: str, chat_history: str) -> str:
        """执行记忆链"""
        return self.memory_chain.invoke({
            "question": question,
            "chat_history": chat_history
        })
