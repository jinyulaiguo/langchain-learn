import os
import sys
from langchain.memory import ConversationBufferWindowMemory

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MEMORY_WINDOW_SIZE

class ConversationMemory:
    """对话记忆管理：使用 LangChain 的 ConversationBufferWindowMemory 实现滑动窗口
    但保持手动的 save_context 以确保检索与记忆的严格隔离。
    """
    
    def __init__(self, window_size: int = MEMORY_WINDOW_SIZE):
        # 初始化 LangChain 的滑动窗口记忆组件
        self.memory = ConversationBufferWindowMemory(
            k=window_size,
            memory_key="chat_history", # 在 Prompt 中引用的变量名
            return_messages=False      # 返回格式化后的纯文本字符串
        )

    def add_turn(self, user_input: str, assistant_response: str):
        """
        向记忆中添加一轮对话。
        隔离说明：
        - 仅手动存入纯净的用户问题和 AI 回答文本。
        - 排除任何检索到的文档 context 或者引用 metadata。
        """
        self.memory.save_context(
            {"input": user_input},
            {"output": assistant_response}
        )
        
    def get_history(self) -> str:
        """获取格式化后的近期对话历史字符串"""
        # load_memory_variables 返回一个字典，包含 memory_key 对应的内容
        vars = self.memory.load_memory_variables({})
        return vars.get("chat_history", "")
    
    def clear(self):
        """清空对话历史"""
        self.memory.clear()
