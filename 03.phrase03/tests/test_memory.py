import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag_system.memory import ConversationMemory

def test_memory_isolation_and_window():
    # 初始化一个窗口大小为 2 的 memory
    memory = ConversationMemory(window_size=2)
    
    # 存入第 1 轮
    memory.add_turn("What is LangChain?", "LangChain is a framework.")
    # 存入第 2 轮
    memory.add_turn("What is RAG?", "Retrieval-Augmented Generation.")
    
    history = memory.get_history()
    assert "What is LangChain?" in history
    assert "Retrieval-Augmented Generation." in history
    
    # 存入第 3 轮，触发窗口截断（第 1 轮应该被遗忘）
    doc_snippet = "Here is some context: ... this should not be in memory"
    final_answer = "RAG combines retrieval and generation."
    # 模拟业务逻辑中，只把纯最终文本 final_answer 存入记忆，而不存 doc_snippet
    memory.add_turn("How does it work?", final_answer)
    
    history2 = memory.get_history()
    # 验证第 1 轮内容被清除
    assert "What is LangChain?" not in history2
    # 验证窗口中存在最后两轮
    assert "What is RAG?" in history2
    assert "How does it work?" in history2
    assert final_answer in history2
    
    # 验证文档片段不会污染历史
    assert doc_snippet not in history2
