import time
from typing import Dict, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class Metrics:
    """Prometheus-ready metrics abstraction."""
    
    def __init__(self) -> None:
        self._request_count: Dict[str, int] = defaultdict(int)
        self._error_count: Dict[str, int] = defaultdict(int)
        self._latency_sum: Dict[str, float] = defaultdict(float)
        self._latency_count: Dict[str, int] = defaultdict(int)
        self._rate_limit_hits: int = 0
        self._circuit_breaker_opens: int = 0
    
    def record_request(self, endpoint: str, status_code: int, latency_sec: float) -> None:
        """Record a request with status and latency."""
        self._request_count[f"{endpoint}_{status_code}"] += 1
        self._latency_sum[endpoint] += latency_sec
        self._latency_count[endpoint] += 1
        
        if status_code >= 400:
            self._error_count[f"{endpoint}_{status_code}"] += 1
    
    def record_rate_limit(self) -> None:
        """Record a rate limit hit."""
        self._rate_limit_hits += 1
    
    def record_circuit_breaker_open(self) -> None:
        """Record a circuit breaker opening."""
        self._circuit_breaker_opens += 1
    
    def get_metrics(self) -> Dict:
        """Get all metrics in Prometheus-ready format."""
        metrics: Dict = {
            "requests_total": dict(self._request_count),
            "errors_total": dict(self._error_count),
            "rate_limit_hits_total": self._rate_limit_hits,
            "circuit_breaker_opens_total": self._circuit_breaker_opens,
        }
        
        # Calculate average latencies
        avg_latencies: Dict[str, float] = {}
        for endpoint, total in self._latency_sum.items():
            count = self._latency_count.get(endpoint, 1)
            avg_latencies[f"{endpoint}_avg_seconds"] = total / count if count > 0 else 0.0
        
        metrics["latency_avg_seconds"] = avg_latencies
        return metrics
    
    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        self._request_count.clear()
        self._error_count.clear()
        self._latency_sum.clear()
        self._latency_count.clear()
        self._rate_limit_hits = 0
        self._circuit_breaker_opens = 0


metrics = Metrics()