from pydantic import BaseModel, Field

class SummaryResult(BaseModel):
    summary: str = Field(description="文章或文本的摘要正文")
    keywords: list[str] = Field(description="核心关键词列表")
    word_count: int = Field(description="输入内容的字数统计")

class TranslationResult(BaseModel):
    translated_text: str = Field(description="翻译后的译文")
    source_lang: str = Field(description="检测到的原文语言")
    confidence: float = Field(description="翻译结果的置信度，范围 0.0 到 1.0")

class CodeExplanation(BaseModel):
    explanation: str = Field(description="代码的作用与原理解释")
    language: str = Field(description="代码所属的编程语言")
    complexity: str = Field(description="代码的复杂度评估：low, medium, 或 high")
    key_concepts: list[str] = Field(description="代码涉及的核心概念列表")

class FallbackResult(BaseModel):
    raw_text: str = Field(description="原始返回内容")
    parse_error: str = Field(description="解析失败的错误信息")
