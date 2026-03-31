from langchain_openai import ChatOpenAI
from langchain_classic.chains import LLMChain
from router_qa.registry import TEMPLATE_REGISTRY
from router_qa.parsers import PARSERS
from router_qa.router import RouterEngine
from router_qa.logger import CallLogger

class RouterQASystem:
    def __init__(self, model_name="gpt-3.5-turbo", temperature=0.7, **kwargs):
        # 允许外部透传额外的 ChatOpenAI 初始化参数（比如 base_url等）
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature, **kwargs)
        self.router = RouterEngine()
        self.logger = CallLogger()
        self.registry = TEMPLATE_REGISTRY
        self.parsers = PARSERS

    def run(self, user_input: str):
        # 1. 执行内部纯文本的确定性路由判定
        route = self.router.route(user_input)
        print(f"[*] 路由判定结果: 采用模板 -> '{route.template_name}'")
        
        # 2. 从注册表中获取对应的提示词模板和解析器
        template = self.registry.get(route.template_name)
        parser = self.parsers.get(route.template_name)
        
        if not template or not parser:
            raise ValueError(f"未找到模板或解析器: {route.template_name}")

        # 将 Pydantic 生成的格式指示注入到调用参数中
        invoke_params = route.extracted_params.copy()
        if "format_instructions" in template.input_variables:
            invoke_params["format_instructions"] = parser.get_format_instructions()
        
        # 3. 显式构建 Chain （完全避开 LCEL 管道操作符）
        chain = LLMChain(llm=self.llm, prompt=template)
        
        # 4. 执行链获取原始回复字符串
        raw_output = chain.invoke(invoke_params)["text"]
        print(f"[*] LLM 原生输出完毕，长度: {len(raw_output)} 字符\n")
        
        # 5. 调用带有 fallback 能力的解析器
        parsed = parser.parse_with_fallback(raw_output)
        
        # 6. 将原始输出及模板名记录进 JSONL 日志中保证可追溯
        self.logger.log(route, raw_output, parsed)
        
        return parsed
