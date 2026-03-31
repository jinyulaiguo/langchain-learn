from langchain_core.prompts import PromptTemplate
from router_qa.parsers import PARSERS

summarizer_prompt = PromptTemplate.from_template(
    "请帮我总结以下文本的主要内容。\n\n"
    "文本：{text}\n\n"
    "{format_instructions}"
)

# 注意在模板中注入了 target_lang 目标语言参数
translator_prompt = PromptTemplate.from_template(
    "请将以下文本翻译为目标语言（{target_lang}）。\n\n"
    "文本：{text}\n\n"
    "{format_instructions}"
)

# 注意在模板中注入了 lang 对应的语言参数
code_explainer_prompt = PromptTemplate.from_template(
    "请详细解释以下 {lang} 代码的作用和原理。\n\n"
    "代码：\n```\n{code}\n```\n\n"
    "{format_instructions}"
)

# 注册表，包含核心的 PromptTemplate 实例
TEMPLATE_REGISTRY = {
    "summarizer": summarizer_prompt,
    "translator": translator_prompt,
    "code_explainer": code_explainer_prompt
}
