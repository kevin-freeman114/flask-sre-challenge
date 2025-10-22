# Chaos Engineering Tests for SRE Resilience Validation
import time
import random
import logging
import requests
import boto3
from typing import List, Dict, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class ChaosExperiment:
    """Base class for chaos engineering experiments"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.start_time = None
        self.end_time = None
        self.results = {}
    
    def setup(self) -> bool:
        """Setup the experiment"""
        logger.info(f"Setting up chaos experiment: {self.name}")
        return True
    
    def execute(self) -> Dict[str, Any]:
        """Execute the chaos experiment"""
        raise NotImplementedError
    
    def teardown(self) -> bool:
        """Cleanup after the experiment"""
        logger.info(f"Tearing down chaos experiment: {self.name}")
        return True
    
    def run(self) -> Dict[str, Any]:
        """Run the complete experiment"""
        self.start_time = datetime.utcnow()
        
        try:
            if not self.setup():
                raise Exception("Setup failed")
            
            self.results = self.execute()
            self.results['status'] = 'completed'
            
        except Exception as e:
            self.results['status'] = 'failed'
            self.results['error'] = str(e)
            logger.error(f"Chaos experiment {self.name} failed: {e}")
        
        finally:
            self.teardown()
            self.end_time = datetime.utcnow()
            self.results['duration'] = (self.end_time - self.start_time).total_seconds()
        
        return self.results

class NetworkLatencyChaos(ChaosExperiment):
    """Simulate network latency issues"""
    
    def __init__(self, target_url: str, latency_ms: int = 1000):
        super().__init__(
            name="network_latency",
            description=f"Simulate {latency_ms}ms network latency"
        )
        self.target_url = target_url
        self.latency_ms = latency_ms
    
    def execute(self) -> Dict[str, Any]:
        """Simulate network latency by adding delays"""
        results = {
            'experiment': self.name,
            'latency_added_ms': self.latency_ms,
            'requests_tested': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0
        }
        
        response_times = []
        
        for i in range(10):  # Test 10 requests
            start_time = time.time()
            
            try:
                # Add artificial delay
                time.sleep(self.latency_ms / 1000.0)
                
                response = requests.get(f"{self.target_url}/health", timeout=5)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000
                response_times.append(response_time)
                
                results['requests_tested'] += 1
                
                if response.status_code == 200:
                    results['successful_requests'] += 1
                else:
                    results['failed_requests'] += 1
                    
            except Exception as e:
                results['failed_requests'] += 1
                logger.error(f"Request failed: {e}")
        
        if response_times:
            results['avg_response_time'] = sum(response_times) / len(response_times)
        
        return results

class DatabaseConnectionChaos(ChaosExperiment):
    """Simulate database connection issues"""
    
    def __init__(self, db_instance_id: str):
        super().__init__(
            name="database_connection_chaos",
            description="Simulate database connection failures"
        )
        self.db_instance_id = db_instance_id
        self.rds_client = boto3.client('rds')
    
    def execute(self) -> Dict[str, Any]:
        """Simulate database connection issues"""
        results = {
            'experiment': self.name,
            'db_instance': self.db_instance_id,
            'actions_taken': [],
            'status': 'completed'
        }
        
        try:
            # Get current DB status
            db_info = self.rds_client.describe_db_instances(
                DBInstanceIdentifier=self.db_instance_id
            )
            
            current_status = db_info['DBInstances'][0]['DBInstanceStatus']
            results['initial_status'] = current_status
            
            # Note: In a real scenario, you might:
            # 1. Temporarily modify security groups to block DB access
            # 2. Restart the DB instance
            # 3. Modify connection limits
            
            # For this example, we'll just log the current state
            results['actions_taken'].append(f"Checked DB status: {current_status}")
            
            # Simulate connection testing
            results['connection_tests'] = self._test_connections()
            
        except Exception as e:
            results['error'] = str(e)
            results['status'] = 'failed'
        
        return results
    
    def _test_connections(self) -> Dict[str, Any]:
        """Test database connections"""
        return {
            'connection_pool_status': 'healthy',
            'active_connections': 5,
            'max_connections': 100,
            'connection_errors': 0
        }

class ECSChaosExperiment(ChaosExperiment):
    """Chaos experiments for ECS services"""
    
    def __init__(self, cluster_name: str, service_name: str):
        super().__init__(
            name="ecs_chaos",
            description="ECS service chaos experiments"
        )
        self.cluster_name = cluster_name
        self.service_name = service_name
        self.ecs_client = boto3.client('ecs')
    
    def execute(self) -> Dict[str, Any]:
        """Execute ECS chaos experiments"""
        results = {
            'experiment': self.name,
            'cluster': self.cluster_name,
            'service': self.service_name,
            'actions': []
        }
        
        try:
            # Get service information
            service_info = self.ecs_client.describe_services(
                cluster=self.cluster_name,
                services=[self.service_name]
            )
            
            service = service_info['services'][0]
            results['initial_desired_count'] = service['desiredCount']
            results['initial_running_count'] = service['runningCount']
            
            # Simulate scaling down (chaos)
            new_desired_count = max(1, service['desiredCount'] - 1)
            
            self.ecs_client.update_service(
                cluster=self.cluster_name,
                service=self.service_name,
                desiredCount=new_desired_count
            )
            
            results['actions'].append(f"Scaled down to {new_desired_count} tasks")
            
            # Wait for scaling to take effect
            time.sleep(30)
            
            # Scale back up
            self.ecs_client.update_service(
                cluster=self.cluster_name,
                service=self.service_name,
                desiredCount=service['desiredCount']
            )
            
            results['actions'].append(f"Scaled back up to {service['desiredCount']} tasks")
            results['status'] = 'completed'
            
        except Exception as e:
            results['error'] = str(e)
            results['status'] = 'failed'
        
        return results

class LoadChaosExperiment(ChaosExperiment):
    """Simulate high load conditions"""
    
    def __init__(self, target_url: str, concurrent_users: int = 50):
        super().__init__(
            name="load_chaos",
            description=f"Simulate {concurrent_users} concurrent users"
        )
        self.target_url = target_url
        self.concurrent_users = concurrent_users
    
    def execute(self) -> Dict[str, Any]:
        """Simulate high load"""
        import threading
        import queue
        
        results = {
            'experiment': self.name,
            'concurrent_users': self.concurrent_users,
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'max_response_time': 0,
            'min_response_time': float('inf')
        }
        
        response_times = []
        result_queue = queue.Queue()
        
        def make_requests():
            """Make requests from a single thread"""
            for _ in range(10):  # 10 requests per thread
                start_time = time.time()
                try:
                    response = requests.get(f"{self.target_url}/api/users", timeout=10)
                    end_time = time.time()
                    
                    response_time = (end_time - start_time) * 1000
                    result_queue.put({
                        'status_code': response.status_code,
                        'response_time': response_time,
                        'success': 200 <= response.status_code < 400
                    })
                except Exception as e:
                    result_queue.put({
                        'status_code': 0,
                        'response_time': 0,
                        'success': False,
                        'error': str(e)
                    })
        
        # Start concurrent threads
        threads = []
        for _ in range(self.concurrent_users):
            thread = threading.Thread(target=make_requests)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        while not result_queue.empty():
            result = result_queue.get()
            results['total_requests'] += 1
            
            if result['success']:
                results['successful_requests'] += 1
            else:
                results['failed_requests'] += 1
            
            response_time = result['response_time']
            response_times.append(response_time)
            
            results['max_response_time'] = max(results['max_response_time'], response_time)
            results['min_response_time'] = min(results['min_response_time'], response_time)
        
        if response_times:
            results['avg_response_time'] = sum(response_times) / len(response_times)
        
        if results['min_response_time'] == float('inf'):
            results['min_response_time'] = 0
        
        return results

class ChaosOrchestrator:
    """Orchestrates chaos engineering experiments"""
    
    def __init__(self):
        self.experiments = []
        self.results = []
    
    def add_experiment(self, experiment: ChaosExperiment):
        """Add an experiment to the orchestration"""
        self.experiments.append(experiment)
    
    def run_experiment(self, experiment_name: str) -> Dict[str, Any]:
        """Run a specific experiment"""
        for experiment in self.experiments:
            if experiment.name == experiment_name:
                logger.info(f"Running chaos experiment: {experiment_name}")
                result = experiment.run()
                self.results.append(result)
                return result
        
        raise ValueError(f"Experiment {experiment_name} not found")
    
    def run_all_experiments(self) -> List[Dict[str, Any]]:
        """Run all experiments"""
        logger.info("Running all chaos experiments")
        
        for experiment in self.experiments:
            try:
                result = experiment.run()
                self.results.append(result)
                
                # Wait between experiments
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Experiment {experiment.name} failed: {e}")
                self.results.append({
                    'experiment': experiment.name,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return self.results
    
    def get_experiment_summary(self) -> Dict[str, Any]:
        """Get summary of all experiments"""
        total_experiments = len(self.results)
        successful_experiments = len([r for r in self.results if r.get('status') == 'completed'])
        failed_experiments = total_experiments - successful_experiments
        
        return {
            'total_experiments': total_experiments,
            'successful_experiments': successful_experiments,
            'failed_experiments': failed_experiments,
            'success_rate': (successful_experiments / total_experiments * 100) if total_experiments > 0 else 0,
            'experiments': self.results
        }

# Example usage and configuration
def create_chaos_experiments(target_url: str, cluster_name: str, service_name: str, db_instance_id: str) -> ChaosOrchestrator:
    """Create a set of chaos experiments"""
    orchestrator = ChaosOrchestrator()
    
    # Add experiments
    orchestrator.add_experiment(NetworkLatencyChaos(target_url, 500))
    orchestrator.add_experiment(ECSChaosExperiment(cluster_name, service_name))
    orchestrator.add_experiment(DatabaseConnectionChaos(db_instance_id))
    orchestrator.add_experiment(LoadChaosExperiment(target_url, 25))
    
    return orchestrator

# Chaos engineering runbook
CHAOS_RUNBOOK = """
# Chaos Engineering Runbook

## Purpose
Validate system resilience and identify failure modes through controlled experiments.

## Pre-Experiment Checklist
- [ ] Notify stakeholders of planned chaos experiments
- [ ] Ensure monitoring is active and alerting is configured
- [ ] Have rollback procedures ready
- [ ] Schedule experiments during low-traffic periods
- [ ] Document baseline metrics

## Experiment Types

### 1. Network Chaos
- **Purpose**: Test network resilience
- **Experiments**: Latency injection, packet loss, network partitions
- **Expected Behavior**: Graceful degradation, circuit breaker activation

### 2. Infrastructure Chaos
- **Purpose**: Test infrastructure resilience
- **Experiments**: Instance termination, scaling events, resource exhaustion
- **Expected Behavior**: Auto-scaling, failover, service recovery

### 3. Application Chaos
- **Purpose**: Test application resilience
- **Experiments**: Memory leaks, CPU exhaustion, dependency failures
- **Expected Behavior**: Circuit breakers, fallback mechanisms, error handling

### 4. Data Chaos
- **Purpose**: Test data layer resilience
- **Experiments**: Database failures, connection pool exhaustion, slow queries
- **Expected Behavior**: Connection pooling, read replicas, caching

## Post-Experiment Analysis
1. **Metrics Analysis**: Compare pre/post experiment metrics
2. **Failure Mode Identification**: Document new failure modes discovered
3. **Improvement Recommendations**: Identify areas for improvement
4. **Documentation Updates**: Update runbooks and procedures

## Safety Guidelines
- Always have rollback procedures ready
- Start with low-impact experiments
- Gradually increase experiment intensity
- Monitor system health throughout experiments
- Stop experiments if critical issues arise
"""

if __name__ == "__main__":
    # Example chaos engineering execution
    orchestrator = create_chaos_experiments(
        target_url="http://your-alb-dns",
        cluster_name="flask-sre-challenge-cluster",
        service_name="flask-sre-challenge-service",
        db_instance_id="flask-sre-challenge-db"
    )
    
    # Run a single experiment
    result = orchestrator.run_experiment("network_latency")
    print(json.dumps(result, indent=2))
    
    # Run all experiments
    # results = orchestrator.run_all_experiments()
    # summary = orchestrator.get_experiment_summary()
    # print(json.dumps(summary, indent=2))
