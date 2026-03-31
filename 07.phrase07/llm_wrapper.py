import os
import time
from typing import Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult
from infrastructure import get_logger, metrics, set_trace_id
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai

logger = get_logger()

class ResilientLLM:
    def __init__(self, primary_model: str = "deepseek-chat", fallback_model: str = "deepseek-chat"):
        # Setup primary with strict timeout
        self.primary = ChatOpenAI(
            model=primary_model,
            api_key=os.getenv("DEEPSEEK_API_KEY") or "dummy_key",
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            timeout=20, # Increased from 10
            max_retries=0 
        )
        
        self.fallback = ChatOpenAI(
            model=fallback_model,
            api_key=os.getenv("DEEPSEEK_API_KEY") or "dummy_key",
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            timeout=60, # Increased from 30
            max_retries=2
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIConnectionError, openai.Timeout)),
        reraise=True
    )
    def _call_with_retry(self, model: ChatOpenAI, messages: List[BaseMessage]) -> Any:
        start_time = time.time()
        model_name = model.model_name
        try:
            response = model.invoke(messages)
            latency = time.time() - start_time
            
            # Extract tokens
            usage = response.usage_metadata if hasattr(response, 'usage_metadata') else {}
            tokens = {
                "prompt": usage.get("input_tokens", 0),
                "completion": usage.get("output_tokens", 0),
                "total": usage.get("total_tokens", 0)
            }
            
            logger.info("llm_call_success", 
                        model=model_name, 
                        latency=latency, 
                        tokens=tokens)
            
            metrics.record(model_name, latency, tokens, True)
            return response
        except Exception as e:
            latency = time.time() - start_time
            logger.error("llm_call_failed", 
                         model=model_name, 
                         error=str(type(e).__name__), 
                         message=str(e))
            metrics.record(model_name, latency, {}, False, error_type=type(e).__name__)
            raise

    def invoke(self, messages: List[BaseMessage]) -> BaseMessage:
        # Step 1: Set trace_id if not exists
        set_trace_id()
        
        try:
            # Try primary first
            return self._call_with_retry(self.primary, messages)
        except Exception as e:
            logger.warning("primary_failed_switching_to_fallback", error=str(e))
            try:
                # Fallback to secondary
                return self.fallback.invoke(messages)
            except Exception as fe:
                logger.error("all_llm_calls_failed_using_safe_mock", error=str(fe))
                # Strategy 3: Safe Mock to ensure pipeline doesn't crash
                return AIMessage(content="[LLM Error: System returned safe mock response due to timeout]")
