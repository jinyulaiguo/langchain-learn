import os
import sys
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag_system.models import RouteDecision
from rag_system.retriever import RetrieverWrapper

class Router:
    """路由层：决定是走记忆路径还是检索路径"""
    
    def __init__(self, retriever: RetrieverWrapper = None):
        self.retriever = retriever if retriever else RetrieverWrapper()
        
    def determine_path(self, user_input: str) -> RouteDecision:
        """
        两阶段路由决策：
        1. 关键词和指令初筛
        2. 如果需要检索，执行检索，并基于分数判断是否降级为记忆路径
        """
        user_input = user_input.strip()
        
        # 显式指令处理
        if user_input.startswith("/search "):
            return self._execute_retrieval(user_input[8:].strip(), "用户显式指定 /search，走检索路径")
        elif user_input.startswith("/chat "):
            return RouteDecision(path="memory", reason="用户显式指定 /chat，走记忆路径")
            
        # 关键词/意图启发式规则 (初筛)
        # 如果提到"刚才", "上一句", "我们谈了什么"等，倾向于走记忆
        memory_keywords = [
            "刚才说的", "上面", "上一句", "我们谈了什么", "刚才", 
            "继续", "所以呢", "然后呢", "再说一次"
        ]
        
        for kw in memory_keywords:
            if kw in user_input:
                return RouteDecision(
                    path="memory", 
                    reason=f"匹配到上下文指代词 '{kw}'，走记忆路径"
                )
        
        # 默认尝试走检索路径 (因为是 RAG 基座系统)，但在执行后会检查阈值
        return self._execute_retrieval(user_input, "默认尝试检索文档上下文")
        
    def _execute_retrieval(self, query: str, initial_reason: str) -> RouteDecision:
        """执行检索，并根据阈值判断是否降级"""
        retrieval_result = self.retriever.retrieve(query)
        
        if retrieval_result.filtered_count == 0:
            # 没有任何片段满足阈值要求 -> 降级到纯记忆路径
            return RouteDecision(
                path="memory",
                reason="检索到的所有文档片段相关性均低于阈值，降级走记忆路径",
                retrieval_result=retrieval_result # 附带供后续透传监控日志
            )
            
        return RouteDecision(
            path="retrieval",
            reason=f"{initial_reason}；且检索到 {retrieval_result.filtered_count} 个相关文档片段",
            retrieval_result=retrieval_result
        )
