import time
from typing import Optional
from dataclasses import dataclass
import logging
from gateway.app.core.metrics import metrics

logger = logging.getLogger(__name__)


@dataclass
class CircuitState:
    """Circuit breaker state for a node."""
    failures: int = 0
    last_failure_time: float = 0.0
    is_open: bool = False
    half_open_attempts: int = 0


class CircuitBreaker:
    """Circuit breaker for node failure handling."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_sec: float = 30.0,
        half_open_max_attempts: int = 3
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout_sec = recovery_timeout_sec
        self._half_open_max_attempts = half_open_max_attempts
        self._circuits: dict[str, CircuitState] = {}
    
    def record_success(self, node_id: str) -> None:
        """Record a successful request to a node."""
        if node_id not in self._circuits:
            return
        
        state = self._circuits[node_id]
        if state.is_open:
            # Transition from half-open to closed
            state.is_open = False
            state.failures = 0
            state.half_open_attempts = 0
            logger.info(f"Circuit breaker closed for node {node_id}")
        else:
            # Reset failure count on success
            state.failures = 0
    
    def record_failure(self, node_id: str) -> None:
        """Record a failed request to a node."""
        if node_id not in self._circuits:
            self._circuits[node_id] = CircuitState()
        
        state = self._circuits[node_id]
        state.failures += 1
        state.last_failure_time = time.time()
        
        if state.failures >= self._failure_threshold and not state.is_open:
            state.is_open = True
            metrics.record_circuit_breaker_open()
            logger.warning(
                f"Circuit breaker opened for node {node_id} "
                f"(failures={state.failures})"
            )
    
    def is_available(self, node_id: str) -> bool:
        """Check if a node is available (circuit not open)."""
        if node_id not in self._circuits:
            return True
        
        state = self._circuits[node_id]
        
        if not state.is_open:
            return True
        
        # Check if recovery timeout has passed
        time_since_failure = time.time() - state.last_failure_time
        if time_since_failure >= self._recovery_timeout_sec:
            # Transition to half-open
            if state.half_open_attempts < self._half_open_max_attempts:
                state.half_open_attempts += 1
                logger.info(
                    f"Circuit breaker half-open for node {node_id} "
                    f"(attempt {state.half_open_attempts})"
                )
                return True
            else:
                # Reset after max half-open attempts
                state.is_open = False
                state.failures = 0
                state.half_open_attempts = 0
                logger.info(f"Circuit breaker reset for node {node_id}")
                return True
        
        return False
    
    def get_state(self, node_id: str) -> Optional[CircuitState]:
        """Get circuit state for a node."""
        return self._circuits.get(node_id)


circuit_breaker = CircuitBreaker()