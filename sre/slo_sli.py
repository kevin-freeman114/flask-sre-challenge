# SRE Service Level Objectives (SLOs) and Service Level Indicators (SLIs)
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

class SLODefinition:
    """Service Level Objective definition"""
    
    def __init__(self, name: str, sli_name: str, target: float, window: int = 30):
        self.name = name
        self.sli_name = sli_name
        self.target = target  # Target percentage (e.g., 99.9 for 99.9%)
        self.window_days = window
        self.description = f"{name}: {target}% over {window} days"

# Define SLOs for the Flask application
SLO_DEFINITIONS = {
    'availability': SLODefinition(
        name="Availability",
        sli_name="availability_sli",
        target=99.9,  # 99.9% availability
        window=30
    ),
    'latency_p95': SLODefinition(
        name="Latency P95",
        sli_name="latency_p95_sli",
        target=95.0,  # 95% of requests under 200ms
        window=30
    ),
    'error_rate': SLODefinition(
        name="Error Rate",
        sli_name="error_rate_sli",
        target=99.0,  # 99% success rate (1% error rate)
        window=30
    ),
    'freshness': SLODefinition(
        name="Data Freshness",
        sli_name="freshness_sli",
        target=99.5,  # 99.5% of data queries return fresh data
        window=7
    )
}

class SLICalculator:
    """Service Level Indicator calculator"""
    
    def __init__(self):
        self.metrics_store = {}  # In production, use CloudWatch or similar
    
    def record_request(self, endpoint: str, status_code: int, response_time: float, timestamp: Optional[datetime] = None):
        """Record a request for SLI calculation"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        key = f"{endpoint}_{timestamp.strftime('%Y-%m-%d-%H')}"
        
        if key not in self.metrics_store:
            self.metrics_store[key] = {
                'total_requests': 0,
                'successful_requests': 0,
                'response_times': [],
                'errors': 0
            }
        
        metrics = self.metrics_store[key]
        metrics['total_requests'] += 1
        
        if 200 <= status_code < 400:
            metrics['successful_requests'] += 1
        else:
            metrics['errors'] += 1
        
        metrics['response_times'].append(response_time)
    
    def calculate_availability_sli(self, start_time: datetime, end_time: datetime) -> float:
        """Calculate availability SLI"""
        total_requests = 0
        successful_requests = 0
        
        current_time = start_time
        while current_time <= end_time:
            key = f"all_{current_time.strftime('%Y-%m-%d-%H')}"
            if key in self.metrics_store:
                metrics = self.metrics_store[key]
                total_requests += metrics['total_requests']
                successful_requests += metrics['successful_requests']
            current_time += timedelta(hours=1)
        
        if total_requests == 0:
            return 100.0
        
        return (successful_requests / total_requests) * 100
    
    def calculate_latency_sli(self, start_time: datetime, end_time: datetime, percentile: float = 95.0) -> float:
        """Calculate latency SLI"""
        all_response_times = []
        
        current_time = start_time
        while current_time <= end_time:
            key = f"all_{current_time.strftime('%Y-%m-%d-%H')}"
            if key in self.metrics_store:
                metrics = self.metrics_store[key]
                all_response_times.extend(metrics['response_times'])
            current_time += timedelta(hours=1)
        
        if not all_response_times:
            return 100.0
        
        # Calculate percentile
        sorted_times = sorted(all_response_times)
        index = int((percentile / 100) * len(sorted_times))
        p95_latency = sorted_times[min(index, len(sorted_times) - 1)]
        
        # SLI: percentage of requests under 200ms
        under_threshold = sum(1 for t in all_response_times if t < 0.2)
        return (under_threshold / len(all_response_times)) * 100
    
    def calculate_error_rate_sli(self, start_time: datetime, end_time: datetime) -> float:
        """Calculate error rate SLI"""
        total_requests = 0
        errors = 0
        
        current_time = start_time
        while current_time <= end_time:
            key = f"all_{current_time.strftime('%Y-%m-%d-%H')}"
            if key in self.metrics_store:
                metrics = self.metrics_store[key]
                total_requests += metrics['total_requests']
                errors += metrics['errors']
            current_time += timedelta(hours=1)
        
        if total_requests == 0:
            return 100.0
        
        success_rate = ((total_requests - errors) / total_requests) * 100
        return success_rate
    
    def calculate_freshness_sli(self, start_time: datetime, end_time: datetime) -> float:
        """Calculate data freshness SLI"""
        # Simplified: assume 99.5% of database queries return fresh data
        # In production, this would track actual data staleness
        return 99.5

class ErrorBudget:
    """Error budget tracking and management"""
    
    def __init__(self, slo: SLODefinition):
        self.slo = slo
        self.budget_consumed = 0.0
        self.budget_total = 100.0 - slo.target  # Error budget percentage
    
    def consume_budget(self, sli_value: float):
        """Consume error budget based on SLI value"""
        if sli_value < self.slo.target:
            consumed = self.slo.target - sli_value
            self.budget_consumed += consumed
            return consumed
        return 0.0
    
    def get_budget_remaining(self) -> float:
        """Get remaining error budget percentage"""
        return max(0, self.budget_total - self.budget_consumed)
    
    def get_budget_remaining_days(self, daily_budget: float) -> float:
        """Get remaining budget in days"""
        if daily_budget <= 0:
            return 0
        return self.get_budget_remaining() / daily_budget
    
    def is_budget_critical(self, threshold: float = 0.5) -> bool:
        """Check if error budget is critically low"""
        return self.get_budget_remaining() < (self.budget_total * threshold)

class SREAlerting:
    """SRE alerting based on SLOs and error budgets"""
    
    def __init__(self):
        self.sli_calculator = SLICalculator()
        self.error_budgets = {
            name: ErrorBudget(slo) for name, slo in SLO_DEFINITIONS.items()
        }
    
    def evaluate_slos(self, start_time: datetime, end_time: datetime) -> Dict[str, Dict]:
        """Evaluate all SLOs and return status"""
        results = {}
        
        for name, slo in SLO_DEFINITIONS.items():
            if name == 'availability':
                sli_value = self.sli_calculator.calculate_availability_sli(start_time, end_time)
            elif name == 'latency_p95':
                sli_value = self.sli_calculator.calculate_latency_sli(start_time, end_time)
            elif name == 'error_rate':
                sli_value = self.sli_calculator.calculate_error_rate_sli(start_time, end_time)
            elif name == 'freshness':
                sli_value = self.sli_calculator.calculate_freshness_sli(start_time, end_time)
            else:
                continue
            
            # Update error budget
            consumed = self.error_budgets[name].consume_budget(sli_value)
            
            results[name] = {
                'slo_target': slo.target,
                'sli_value': sli_value,
                'status': 'PASS' if sli_value >= slo.target else 'FAIL',
                'budget_consumed': consumed,
                'budget_remaining': self.error_budgets[name].get_budget_remaining(),
                'is_critical': self.error_budgets[name].is_budget_critical()
            }
        
        return results
    
    def should_alert(self, results: Dict[str, Dict]) -> List[str]:
        """Determine if alerts should be triggered"""
        alerts = []
        
        for name, result in results.items():
            if result['status'] == 'FAIL':
                alerts.append(f"SLO VIOLATION: {name} - {result['sli_value']:.2f}% < {result['slo_target']:.2f}%")
            
            if result['is_critical']:
                alerts.append(f"ERROR BUDGET CRITICAL: {name} - {result['budget_remaining']:.2f}% remaining")
        
        return alerts

# SRE Dashboard data structure
class SREDashboard:
    """SRE Dashboard for monitoring SLOs and error budgets"""
    
    def __init__(self):
        self.alerting = SREAlerting()
    
    def get_dashboard_data(self) -> Dict:
        """Get comprehensive SRE dashboard data"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)
        
        slo_results = self.alerting.evaluate_slos(start_time, end_time)
        alerts = self.alerting.should_alert(slo_results)
        
        return {
            'timestamp': end_time.isoformat(),
            'window': '30 days',
            'slos': slo_results,
            'alerts': alerts,
            'overall_status': 'HEALTHY' if not alerts else 'DEGRADED',
            'recommendations': self._get_recommendations(slo_results)
        }
    
    def _get_recommendations(self, slo_results: Dict[str, Dict]) -> List[str]:
        """Get recommendations based on SLO status"""
        recommendations = []
        
        for name, result in slo_results.items():
            if result['status'] == 'FAIL':
                if name == 'availability':
                    recommendations.append("Investigate infrastructure issues and implement redundancy")
                elif name == 'latency_p95':
                    recommendations.append("Optimize database queries and implement caching")
                elif name == 'error_rate':
                    recommendations.append("Review error logs and implement better error handling")
                elif name == 'freshness':
                    recommendations.append("Check database replication lag and query performance")
        
        return recommendations

# Export instances for use in the application
sli_calculator = SLICalculator()
sre_dashboard = SREDashboard()
