import os
import json
import datetime
from router_qa.router import RouteResult
from pydantic import BaseModel

class CallLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "router_calls.jsonl")

    def log(self, route: RouteResult, raw_output: str, parsed_result: BaseModel):
        # 若是 FallbackResult 则表示解析失败了
        parse_success = type(parsed_result).__name__ != "FallbackResult"
        
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "template_name": route.template_name,
            "user_input_params": route.extracted_params,
            "raw_llm_output": raw_output,
            "parse_success": parse_success,
            "parsed_result": parsed_result.model_dump()
        }
        
        # 以 JSONL 的格式追加一条记录
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
