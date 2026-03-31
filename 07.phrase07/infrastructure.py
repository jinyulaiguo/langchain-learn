import os
import time
import uuid
import structlog
import json
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variable to store trace_id for the current request
_trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")

def setup_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def set_trace_id(trace_id: Optional[str] = None):
    if not trace_id:
        trace_id = str(uuid.uuid4())
    _trace_id_ctx.set(trace_id)
    structlog.contextvars.bind_contextvars(trace_id=trace_id)
    return trace_id

def get_logger():
    return structlog.get_logger()

class MetricsCollector:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricsCollector, cls).__new__(cls)
            cls._instance.metrics = []
        return cls._instance

    def record(self, model: str, latency: float, tokens: Dict[str, int], success: bool, error_type: Optional[str] = None):
        self.metrics.append({
            "timestamp": time.time(),
            "model": model,
            "latency": latency,
            "tokens": tokens,
            "success": success,
            "error_type": error_type
        })

    def get_report(self):
        if not self.metrics:
            return "No metrics collected yet."
        
        successes = [m for m in self.metrics if m["success"]]
        latencies = sorted([m["latency"] for m in successes])
        total = len(self.metrics)
        success_count = len(successes)
        
        report = {
            "total_requests": total,
            "success_rate": f"{(success_count / total * 100):.2f}%" if total > 0 else "0%",
            "p50_latency": f"{latencies[len(latencies)//2]:.4f}s" if latencies else "N/A",
            "p95_latency": f"{latencies[int(len(latencies)*0.95)]:.4f}s" if latencies else "N/A",
            "error_distribution": {}
        }
        
        for m in self.metrics:
            if not m["success"]:
                err = m["error_type"] or "Unknown"
                report["error_distribution"][err] = report["error_distribution"].get(err, 0) + 1
        
        return report

metrics = MetricsCollector()
