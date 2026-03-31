import re
from dataclasses import dataclass

@dataclass
class RouteResult:
    template_name: str
    extracted_params: dict

class RouterEngine:
    def __init__(self):
        # 按优先级配置的路由规则（因为列表有序，所以优先匹配先定义的规则）
        self.routes = [
            {
                "name": "code_explainer",
                "keywords": ["def ", "class ", "function", "bug", "报错", "代码", "code", "import", "error", "代码解释"],
            },
            {
                "name": "translator",
                "keywords": ["翻译", "translate", "英文", "中文", "日语", "into english", "转换语言"],
            },
            {
                "name": "summarizer",
                "keywords": ["总结", "摘要", "summarize", "概括", "提炼"],
            }
        ]

    def route(self, user_input: str) -> RouteResult:
        user_input_lower = user_input.lower()
        selected_template = "summarizer" # 默认兜底
        
        for route in self.routes:
            if any(kw.lower() in user_input_lower for kw in route["keywords"]):
                selected_template = route["name"]
                break
                
        # 提取各个模板需要的额外参数
        params = {"text": user_input} # 基础参数，部分模板需要
        
        if selected_template == "translator":
            # 简单启发式提取目标语言
            if "英文" in user_input or "english" in user_input_lower:
                params["target_lang"] = "English"
            elif "日语" in user_input or "japanese" in user_input_lower:
                params["target_lang"] = "Japanese"
            else:
                params["target_lang"] = "Chinese" # 默认翻译为中文
                
        elif selected_template == "code_explainer":
            # 代码解释器不需要 text 参数，但需要 code 和 lang
            params.pop("text", None)
            params["code"] = user_input
            
            # 这里简单做语言推断
            if "def " in user_input or "import " in user_input:
                params["lang"] = "Python"
            elif "function" in user_input_lower or "const " in user_input:
                params["lang"] = "JavaScript"
            else:
                params["lang"] = "Unknown"
        
        return RouteResult(
            template_name=selected_template,
            extracted_params=params
        )
