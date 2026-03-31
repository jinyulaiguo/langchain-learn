import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag_system.models import RouteDecision

class ResponseFormatter:
    """对 LLM 的原始输出进行格式化，附加检索来源、匹配分数等元信息"""

    @staticmethod
    def format(llm_response: str, decision: RouteDecision) -> str:
        """
        格式化完整的输出文本
        """
        lines = []
        lines.append("📝 回答：")
        lines.append(llm_response.strip())
        lines.append("")
        
        path_name = "检索路径 (Retrieval Path)" if decision.path == "retrieval" else "记忆路径 (Memory Path)"
        lines.append(f"📂 回答路径：{path_name}")
        lines.append(f"💡 决策原因：{decision.reason}")
        
        # 附加检索元数据
        if decision.retrieval_result:
            res = decision.retrieval_result
            lines.append("📊 检索元数据：")
            lines.append(f"  - 初始召回数量：{res.total_retrieved}")
            lines.append(f"  - 过滤后剩余数：{res.filtered_count}")
            
            if res.documents:
                top_score = f"{res.documents[0].score:.4f}"
            else:
                top_score = "N/A"
            lines.append(f"  - Top-1 分数：{top_score}")
            lines.append("")
            
            # 附加详细来源引用
            if res.documents and decision.path == "retrieval":
                lines.append("📎 引用来源：")
                for i, doc in enumerate(res.documents, 1):
                    page_info = f" | 页码: {doc.page}" if doc.page != -1 and doc.page is not None else ""
                    lines.append(f"  [{i}] {doc.source}{page_info} | Chunk ID: {doc.chunk_id} | 分数: {doc.score:.4f}")
                    # 显示包含片段前缀，用以验证内容
                    snippet = doc.content[:60].replace("\n", " ") + "..." if len(doc.content) > 60 else doc.content.replace("\n", " ")
                    lines.append(f"      \"{snippet}\"")
        
        return "\n".join(lines)
