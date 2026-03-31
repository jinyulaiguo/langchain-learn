import pytest
import os
from unittest.mock import MagicMock, patch
from llm_wrapper import ResilientLLM
from infrastructure import metrics, MetricsCollector
from langchain_core.messages import HumanMessage, AIMessage
import openai

@pytest.fixture(autouse=True)
def reset_metrics():
    # Reset metrics before each test
    metrics.metrics = []

def test_fallback_mechanism():
    """
    Test that when the primary model fails with a connection error,
    it falls back to the secondary model.
    """
    with patch("langchain_openai.ChatOpenAI.invoke") as mock_invoke:
        # Mocking primary failure then secondary success
        # primary is called first (possibly with retries if it's a retryable error)
        # For simplicity, let's make it fail with a non-retryable for this test or 
        # let it exhaust retries.
        
        # Side effect: 1. ConnectionError (Primary), 2. Success (Fallback)
        mock_invoke.side_effect = [
            openai.APIConnectionError(message="Primary Failed", request=None),
            AIMessage(content="Fallback response", usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})
        ]
        
        llm = ResilientLLM()
        # We need to ensure the primary fails and the fallback is invoked
        # Invoking once
        response = llm.invoke([HumanMessage(content="test")])
        
        assert response.content == "Fallback response"
        assert len(metrics.metrics) >= 2 # At least one failure and one success
        assert any(not m["success"] for m in metrics.metrics)
        assert any(m["success"] for m in metrics.metrics)

def test_tracing_not_blocking():
    """
    Verify that if LangSmith environment variables are missing/configured off,
    the system still runs (LangChain handles this usually, but we verify our wrapper doesn't break).
    """
    with patch.dict(os.environ, {"LANGCHAIN_TRACING_V2": "false"}):
        llm = ResilientLLM()
        with patch("langchain_openai.ChatOpenAI.invoke") as mock_invoke:
            mock_invoke.return_value = AIMessage(content="OK", usage_metadata={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2})
            response = llm.invoke([HumanMessage(content="hi")])
            assert response.content == "OK"

def test_health_report_generation():
    coll = MetricsCollector()
    coll.metrics = []
    coll.record("model-a", 0.5, {"total": 10}, True)
    coll.record("model-a", 1.5, {"total": 20}, True)
    coll.record("model-a", 1.0, {"total": 15}, False, error_type="Timeout")
    
    report = coll.get_report()
    assert report["total_requests"] == 3
    assert report["success_rate"] == "66.67%"
    assert report["error_distribution"]["Timeout"] == 1
