# Circuit Breaker Pattern Implementation for SRE Resilience
import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from functools import wraps
import threading

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back

class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass

class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception,
                 name: str = "default"):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = threading.Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized with threshold={failure_threshold}, timeout={recovery_timeout}s")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker '{self.name}' moved to HALF_OPEN state")
                else:
                    raise CircuitBreakerError(f"Circuit breaker '{self.name}' is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info(f"Circuit breaker '{self.name}' reset to CLOSED state")
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' opened after {self.failure_count} failures")
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'last_failure_time': self.last_failure_time,
            'threshold': self.failure_threshold,
            'timeout': self.recovery_timeout
        }

# Circuit breaker decorator
def circuit_breaker(failure_threshold: int = 5, 
                    recovery_timeout: int = 60,
                    expected_exception: type = Exception,
                    name: Optional[str] = None):
    """Decorator to add circuit breaker functionality"""
    def decorator(func):
        cb_name = name or f"{func.__module__}.{func.__name__}"
        breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            name=cb_name
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        # Add circuit breaker instance to wrapper for monitoring
        wrapper._circuit_breaker = breaker
        return wrapper
    return decorator

# Database circuit breaker
class DatabaseCircuitBreaker:
    """Specialized circuit breaker for database operations"""
    
    def __init__(self):
        self.breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=Exception,
            name="database"
        )
    
    def execute_query(self, query_func: Callable, *args, **kwargs):
        """Execute database query with circuit breaker protection"""
        try:
            return self.breaker.call(query_func, *args, **kwargs)
        except CircuitBreakerError:
            logger.error("Database circuit breaker is OPEN - returning cached/default data")
            # Return cached data or default response
            return self._get_fallback_data()
    
    def _get_fallback_data(self):
        """Return fallback data when database is unavailable"""
        return {
            'users': [],
            'error': 'Database temporarily unavailable',
            'fallback': True
        }

# External service circuit breaker
class ExternalServiceCircuitBreaker:
    """Circuit breaker for external service calls"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception,
            name=f"external_{service_name}"
        )
    
    def call_service(self, service_func: Callable, *args, **kwargs):
        """Call external service with circuit breaker protection"""
        try:
            return self.breaker.call(service_func, *args, **kwargs)
        except CircuitBreakerError:
            logger.warning(f"External service '{self.service_name}' circuit breaker is OPEN")
            return self._get_service_fallback()
    
    def _get_service_fallback(self):
        """Return fallback response for external service"""
        return {
            'error': f'Service {self.service_name} temporarily unavailable',
            'fallback': True
        }

# Circuit breaker manager for monitoring
class CircuitBreakerManager:
    """Manager for monitoring all circuit breakers"""
    
    def __init__(self):
        self.breakers = {}
    
    def register_breaker(self, name: str, breaker: CircuitBreaker):
        """Register a circuit breaker for monitoring"""
        self.breakers[name] = breaker
    
    def get_all_states(self) -> dict:
        """Get states of all registered circuit breakers"""
        return {
            name: breaker.get_state() 
            for name, breaker in self.breakers.items()
        }
    
    def get_open_circuits(self) -> list:
        """Get list of open circuit breakers"""
        return [
            name for name, breaker in self.breakers.items()
            if breaker.state == CircuitState.OPEN
        ]
    
    def get_critical_circuits(self) -> list:
        """Get circuit breakers that are in critical state"""
        critical = []
        for name, breaker in self.breakers.items():
            if breaker.state == CircuitState.OPEN:
                # Check if it's been open for too long
                if breaker.last_failure_time:
                    time_open = time.time() - breaker.last_failure_time
                    if time_open > breaker.recovery_timeout * 2:  # Been open too long
                        critical.append(name)
        return critical

# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()

# Database circuit breaker instance
db_circuit_breaker = DatabaseCircuitBreaker()

# Example usage with decorator
@circuit_breaker(failure_threshold=3, recovery_timeout=30, name="user_creation")
def create_user_with_circuit_breaker(user_data):
    """Example function with circuit breaker protection"""
    # This would be your actual user creation logic
    # The circuit breaker will protect against failures
    pass
