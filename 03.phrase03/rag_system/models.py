from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class RetrievedDocument(BaseModel):
    """单条检索到的文档片段"""
    content: str = Field(description="文档片段的原始内容")
    score: float = Field(description="相关性分数，范围 0-1")
    source: str = Field(description="来源文件名或路径")
    page: Optional[int] = Field(default=None, description="来源页码（可选）")
    chunk_id: str = Field(description="文档块的唯一标识符（例如在文档中的索引）")

class RetrievalResult(BaseModel):
    """一次检索操作的完整结果"""
    query: str = Field(description="执行检索的原始查询字符串")
    total_retrieved: int = Field(description="向量数据库最初召回的文档总数")
    filtered_count: int = Field(description="通过相关性阈值过滤后保留的文档数")
    documents: List[RetrievedDocument] = Field(default_factory=list, description="最终候选的文档片段列表")

class RouteDecision(BaseModel):
    """路由引擎对查询的路径决策"""
    path: Literal["retrieval", "memory"] = Field(description="路由路径选择：'retrieval' 或 'memory'")
    reason: str = Field(description="作出此路由决策的原因描述")
    retrieval_result: Optional[RetrievalResult] = Field(default=None, description="如果执行了检索（如分数低于阈值被降级），附带检索结果供后续阶段（如格式化）使用")
