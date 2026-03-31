import json
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from router_qa.models import SummaryResult, TranslationResult, CodeExplanation, FallbackResult

class FallbackAwareParser:
    def __init__(self, pydantic_obj):
        self.parser = PydanticOutputParser(pydantic_object=pydantic_obj)
        self.pydantic_obj = pydantic_obj
        
    def get_format_instructions(self) -> str:
        return self.parser.get_format_instructions()
        
    def parse_with_fallback(self, raw_output: str) -> BaseModel:
        try:
            return self.parser.parse(raw_output)
        except OutputParserException as e:
            print(f"[Warning] Failed to parse output: {str(e)}")
            return FallbackResult(raw_text=raw_output, parse_error=str(e))
        except Exception as e:
            print(f"[Warning] Unknown error during parse: {str(e)}")
            return FallbackResult(raw_text=raw_output, parse_error=str(e))

PARSERS = {
    "summarizer": FallbackAwareParser(SummaryResult),
    "translator": FallbackAwareParser(TranslationResult),
    "code_explainer": FallbackAwareParser(CodeExplanation)
}
