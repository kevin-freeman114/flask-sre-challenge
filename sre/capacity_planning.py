# Capacity Planning and Auto-Scaling Policies for SRE
import boto3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import math

logger = logging.getLogger(__name__)

class CapacityPlanner:
    """Capacity planning for infrastructure resources"""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.ecs = boto3.client('ecs')
        self.rds = boto3.client('rds')
    
    def analyze_current_capacity(self, cluster_name: str, service_name: str) -> Dict[str, Any]:
        """Analyze current capacity utilization"""
        analysis = {
            'timestamp': datetime.utcnow().isoformat(),
            'cluster': cluster_name,
            'service': service_name,
            'metrics': {}
        }
        
        try:
            # Get ECS service information
            service_info = self.ecs.describe_services(
                cluster=cluster_name,
                services=[service_name]
            )
            
            service = service_info['services'][0]
            analysis['metrics']['ecs'] = {
                'desired_count': service['desiredCount'],
                'running_count': service['runningCount'],
                'pending_count': service['pendingCount'],
                'cpu_utilization': self._get_cpu_utilization(cluster_name, service_name),
                'memory_utilization': self._get_memory_utilization(cluster_name, service_name)
            }
            
            # Get RDS metrics
            analysis['metrics']['rds'] = self._get_rds_metrics()
            
            # Get ALB metrics
            analysis['metrics']['alb'] = self._get_alb_metrics()
            
        except Exception as e:
            logger.error(f"Failed to analyze capacity: {e}")
            analysis['error'] = str(e)
        
        return analysis
    
    def _get_cpu_utilization(self, cluster_name: str, service_name: str) -> float:
        """Get average CPU utilization"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ECS',
                MetricName='CPUUtilization',
                Dimensions=[
                    {'Name': 'ClusterName', 'Value': cluster_name},
                    {'Name': 'ServiceName', 'Value': service_name}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                return response['Datapoints'][-1]['Average']
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to get CPU utilization: {e}")
            return 0.0
    
    def _get_memory_utilization(self, cluster_name: str, service_name: str) -> float:
        """Get average memory utilization"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ECS',
                MetricName='MemoryUtilization',
                Dimensions=[
                    {'Name': 'ClusterName', 'Value': cluster_name},
                    {'Name': 'ServiceName', 'Value': service_name}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                return response['Datapoints'][-1]['Average']
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to get memory utilization: {e}")
            return 0.0
    
    def _get_rds_metrics(self) -> Dict[str, Any]:
        """Get RDS performance metrics"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            metrics = {}
            
            # CPU Utilization
            cpu_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': 'flask-sre-challenge-db'}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            if cpu_response['Datapoints']:
                metrics['cpu_utilization'] = cpu_response['Datapoints'][-1]['Average']
            
            # Database Connections
            conn_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='DatabaseConnections',
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': 'flask-sre-challenge-db'}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            if conn_response['Datapoints']:
                metrics['connections'] = conn_response['Datapoints'][-1]['Average']
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get RDS metrics: {e}")
            return {}
    
    def _get_alb_metrics(self) -> Dict[str, Any]:
        """Get ALB performance metrics"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            metrics = {}
            
            # Request Count
            request_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ApplicationELB',
                MetricName='RequestCount',
                Dimensions=[{'Name': 'LoadBalancer', 'Value': 'app/flask-sre-challenge-alb'}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )
            
            if request_response['Datapoints']:
                metrics['request_count'] = sum(dp['Sum'] for dp in request_response['Datapoints'])
            
            # Response Time
            response_time_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ApplicationELB',
                MetricName='TargetResponseTime',
                Dimensions=[{'Name': 'LoadBalancer', 'Value': 'app/flask-sre-challenge-alb'}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            if response_time_response['Datapoints']:
                metrics['avg_response_time'] = response_time_response['Datapoints'][-1]['Average']
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get ALB metrics: {e}")
            return {}
    
    def predict_capacity_needs(self, 
                             current_metrics: Dict[str, Any],
                             growth_rate: float = 0.1,
                             time_horizon_days: int = 30) -> Dict[str, Any]:
        """Predict capacity needs based on current metrics and growth"""
        
        predictions = {
            'timestamp': datetime.utcnow().isoformat(),
            'growth_rate': growth_rate,
            'time_horizon_days': time_horizon_days,
            'predictions': {}
        }
        
        try:
            ecs_metrics = current_metrics.get('metrics', {}).get('ecs', {})
            rds_metrics = current_metrics.get('metrics', {}).get('rds', {})
            alb_metrics = current_metrics.get('metrics', {}).get('alb', {})
            
            # ECS Capacity Predictions
            if ecs_metrics:
                current_cpu = ecs_metrics.get('cpu_utilization', 0)
                current_memory = ecs_metrics.get('memory_utilization', 0)
                current_tasks = ecs_metrics.get('running_count', 1)
                
                # Predict based on growth rate
                future_cpu = current_cpu * (1 + growth_rate) ** (time_horizon_days / 30)
                future_memory = current_memory * (1 + growth_rate) ** (time_horizon_days / 30)
                
                # Calculate required tasks
                cpu_tasks_needed = math.ceil(current_tasks * (future_cpu / 70))  # Target 70% CPU
                memory_tasks_needed = math.ceil(current_tasks * (future_memory / 80))  # Target 80% memory
                
                predictions['predictions']['ecs'] = {
                    'current_tasks': current_tasks,
                    'predicted_cpu_utilization': future_cpu,
                    'predicted_memory_utilization': future_memory,
                    'recommended_tasks': max(cpu_tasks_needed, memory_tasks_needed),
                    'scaling_factor': max(cpu_tasks_needed, memory_tasks_needed) / current_tasks
                }
            
            # RDS Capacity Predictions
            if rds_metrics:
                current_cpu = rds_metrics.get('cpu_utilization', 0)
                current_connections = rds_metrics.get('connections', 0)
                
                future_cpu = current_cpu * (1 + growth_rate) ** (time_horizon_days / 30)
                future_connections = current_connections * (1 + growth_rate) ** (time_horizon_days / 30)
                
                predictions['predictions']['rds'] = {
                    'current_cpu_utilization': current_cpu,
                    'current_connections': current_connections,
                    'predicted_cpu_utilization': future_cpu,
                    'predicted_connections': future_connections,
                    'recommendation': 'scale_up' if future_cpu > 70 else 'monitor'
                }
            
            # ALB Capacity Predictions
            if alb_metrics:
                current_requests = alb_metrics.get('request_count', 0)
                current_response_time = alb_metrics.get('avg_response_time', 0)
                
                future_requests = current_requests * (1 + growth_rate) ** (time_horizon_days / 30)
                
                predictions['predictions']['alb'] = {
                    'current_requests_per_hour': current_requests,
                    'current_avg_response_time': current_response_time,
                    'predicted_requests_per_hour': future_requests,
                    'recommendation': 'scale_up' if future_response_time > 0.5 else 'monitor'
                }
        
        except Exception as e:
            logger.error(f"Failed to predict capacity needs: {e}")
            predictions['error'] = str(e)
        
        return predictions

class AutoScalingPolicy:
    """Auto-scaling policies for ECS services"""
    
    def __init__(self, cluster_name: str, service_name: str):
        self.cluster_name = cluster_name
        self.service_name = service_name
        self.application_autoscaling = boto3.client('application-autoscaling')
    
    def create_scaling_policy(self, 
                             metric_type: str = 'CPUUtilization',
                             target_value: float = 70.0,
                             scale_out_cooldown: int = 300,
                             scale_in_cooldown: int = 300,
                             min_capacity: int = 1,
                             max_capacity: int = 10) -> Dict[str, Any]:
        """Create auto-scaling policy for ECS service"""
        
        resource_id = f"service/{self.cluster_name}/{self.service_name}"
        
        try:
            # Register scalable target
            self.application_autoscaling.register_scalable_target(
                ServiceNamespace='ecs',
                ResourceId=resource_id,
                ScalableDimension='ecs:service:DesiredCount',
                MinCapacity=min_capacity,
                MaxCapacity=max_capacity
            )
            
            # Create scaling policy
            policy_name = f"{self.service_name}-scaling-policy"
            
            self.application_autoscaling.put_scaling_policy(
                ServiceNamespace='ecs',
                ResourceId=resource_id,
                ScalableDimension='ecs:service:DesiredCount',
                PolicyName=policy_name,
                PolicyType='TargetTrackingScaling',
                TargetTrackingScalingPolicyConfiguration={
                    'TargetValue': target_value,
                    'PredefinedMetricSpecification': {
                        'PredefinedMetricType': metric_type
                    },
                    'ScaleOutCooldown': scale_out_cooldown,
                    'ScaleInCooldown': scale_in_cooldown
                }
            )
            
            return {
                'status': 'success',
                'policy_name': policy_name,
                'resource_id': resource_id,
                'target_value': target_value,
                'min_capacity': min_capacity,
                'max_capacity': max_capacity
            }
            
        except Exception as e:
            logger.error(f"Failed to create scaling policy: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def create_custom_scaling_policy(self, 
                                   metric_namespace: str,
                                   metric_name: str,
                                   target_value: float,
                                   dimensions: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create custom metric scaling policy"""
        
        resource_id = f"service/{self.cluster_name}/{self.service_name}"
        policy_name = f"{self.service_name}-custom-scaling-policy"
        
        try:
            metric_spec = {
                'TargetValue': target_value,
                'CustomizedMetricSpecification': {
                    'MetricName': metric_name,
                    'Namespace': metric_namespace,
                    'Statistic': 'Average'
                },
                'ScaleOutCooldown': 300,
                'ScaleInCooldown': 300
            }
            
            if dimensions:
                metric_spec['CustomizedMetricSpecification']['Dimensions'] = dimensions
            
            self.application_autoscaling.put_scaling_policy(
                ServiceNamespace='ecs',
                ResourceId=resource_id,
                ScalableDimension='ecs:service:DesiredCount',
                PolicyName=policy_name,
                PolicyType='TargetTrackingScaling',
                TargetTrackingScalingPolicyConfiguration=metric_spec
            )
            
            return {
                'status': 'success',
                'policy_name': policy_name,
                'metric_namespace': metric_namespace,
                'metric_name': metric_name,
                'target_value': target_value
            }
            
        except Exception as e:
            logger.error(f"Failed to create custom scaling policy: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def get_scaling_policies(self) -> List[Dict[str, Any]]:
        """Get existing scaling policies"""
        try:
            resource_id = f"service/{self.cluster_name}/{self.service_name}"
            
            response = self.application_autoscaling.describe_scaling_policies(
                ServiceNamespace='ecs',
                ResourceId=resource_id
            )
            
            return response.get('ScalingPolicies', [])
            
        except Exception as e:
            logger.error(f"Failed to get scaling policies: {e}")
            return []
    
    def delete_scaling_policy(self, policy_name: str) -> Dict[str, Any]:
        """Delete a scaling policy"""
        try:
            resource_id = f"service/{self.cluster_name}/{self.service_name}"
            
            self.application_autoscaling.delete_scaling_policy(
                ServiceNamespace='ecs',
                ResourceId=resource_id,
                ScalableDimension='ecs:service:DesiredCount',
                PolicyName=policy_name
            )
            
            return {
                'status': 'success',
                'policy_name': policy_name,
                'message': 'Scaling policy deleted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete scaling policy: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }

class CapacityRecommendations:
    """Generate capacity recommendations based on analysis"""
    
    def __init__(self):
        self.capacity_planner = CapacityPlanner()
    
    def generate_recommendations(self, 
                               cluster_name: str, 
                               service_name: str,
                               growth_rate: float = 0.1) -> Dict[str, Any]:
        """Generate comprehensive capacity recommendations"""
        
        recommendations = {
            'timestamp': datetime.utcnow().isoformat(),
            'cluster': cluster_name,
            'service': service_name,
            'recommendations': []
        }
        
        try:
            # Analyze current capacity
            current_analysis = self.capacity_planner.analyze_current_capacity(cluster_name, service_name)
            
            # Predict future needs
            predictions = self.capacity_planner.predict_capacity_needs(current_analysis, growth_rate)
            
            # Generate recommendations
            recommendations['recommendations'] = self._analyze_recommendations(current_analysis, predictions)
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            recommendations['error'] = str(e)
        
        return recommendations
    
    def _analyze_recommendations(self, 
                               current_analysis: Dict[str, Any],
                               predictions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze and generate specific recommendations"""
        
        recs = []
        
        try:
            ecs_metrics = current_analysis.get('metrics', {}).get('ecs', {})
            rds_metrics = current_analysis.get('metrics', {}).get('rds', {})
            alb_metrics = current_analysis.get('metrics', {}).get('alb', {})
            
            # ECS Recommendations
            if ecs_metrics:
                cpu_util = ecs_metrics.get('cpu_utilization', 0)
                memory_util = ecs_metrics.get('memory_utilization', 0)
                current_tasks = ecs_metrics.get('running_count', 1)
                
                if cpu_util > 80:
                    recs.append({
                        'component': 'ECS',
                        'priority': 'HIGH',
                        'issue': 'High CPU utilization',
                        'current_value': f"{cpu_util:.1f}%",
                        'recommendation': 'Scale out ECS service or optimize application code',
                        'action': 'Increase desired count or optimize CPU usage'
                    })
                
                if memory_util > 85:
                    recs.append({
                        'component': 'ECS',
                        'priority': 'HIGH',
                        'issue': 'High memory utilization',
                        'current_value': f"{memory_util:.1f}%",
                        'recommendation': 'Scale out ECS service or optimize memory usage',
                        'action': 'Increase desired count or optimize memory usage'
                    })
                
                if current_tasks < 2:
                    recs.append({
                        'component': 'ECS',
                        'priority': 'MEDIUM',
                        'issue': 'Single point of failure',
                        'current_value': f"{current_tasks} tasks",
                        'recommendation': 'Run at least 2 tasks for high availability',
                        'action': 'Increase desired count to 2 or more'
                    })
            
            # RDS Recommendations
            if rds_metrics:
                cpu_util = rds_metrics.get('cpu_utilization', 0)
                connections = rds_metrics.get('connections', 0)
                
                if cpu_util > 70:
                    recs.append({
                        'component': 'RDS',
                        'priority': 'HIGH',
                        'issue': 'High database CPU utilization',
                        'current_value': f"{cpu_util:.1f}%",
                        'recommendation': 'Consider scaling up RDS instance or optimizing queries',
                        'action': 'Upgrade instance class or optimize database queries'
                    })
                
                if connections > 80:
                    recs.append({
                        'component': 'RDS',
                        'priority': 'MEDIUM',
                        'issue': 'High connection count',
                        'current_value': f"{connections:.0f} connections",
                        'recommendation': 'Monitor connection pool and consider read replicas',
                        'action': 'Implement connection pooling or add read replicas'
                    })
            
            # ALB Recommendations
            if alb_metrics:
                response_time = alb_metrics.get('avg_response_time', 0)
                
                if response_time > 0.5:  # 500ms
                    recs.append({
                        'component': 'ALB',
                        'priority': 'MEDIUM',
                        'issue': 'High response time',
                        'current_value': f"{response_time:.3f}s",
                        'recommendation': 'Optimize application performance or scale out',
                        'action': 'Profile application and consider scaling'
                    })
        
        except Exception as e:
            logger.error(f"Failed to analyze recommendations: {e}")
            recs.append({
                'component': 'SYSTEM',
                'priority': 'HIGH',
                'issue': 'Analysis failed',
                'recommendation': 'Check system health and monitoring',
                'action': 'Investigate system issues'
            })
        
        return recs

# Example usage and configuration
def setup_auto_scaling(cluster_name: str, service_name: str) -> Dict[str, Any]:
    """Set up comprehensive auto-scaling for ECS service"""
    
    auto_scaler = AutoScalingPolicy(cluster_name, service_name)
    
    # Create CPU-based scaling policy
    cpu_policy = auto_scaler.create_scaling_policy(
        metric_type='ECSServiceAverageCPUUtilization',
        target_value=70.0,
        min_capacity=2,
        max_capacity=10
    )
    
    # Create memory-based scaling policy
    memory_policy = auto_scaler.create_scaling_policy(
        metric_type='ECSServiceAverageMemoryUtilization',
        target_value=80.0,
        min_capacity=2,
        max_capacity=10
    )
    
    # Create custom metric scaling policy (e.g., request rate)
    custom_policy = auto_scaler.create_custom_scaling_policy(
        metric_namespace='AWS/ApplicationELB',
        metric_name='RequestCount',
        target_value=1000.0,  # Target 1000 requests per minute
        dimensions=[{'Name': 'LoadBalancer', 'Value': 'app/flask-sre-challenge-alb'}]
    )
    
    return {
        'cpu_policy': cpu_policy,
        'memory_policy': memory_policy,
        'custom_policy': custom_policy
    }

if __name__ == "__main__":
    # Example capacity planning execution
    planner = CapacityPlanner()
    recommendations = CapacityRecommendations()
    
    # Analyze current capacity
    analysis = planner.analyze_current_capacity(
        cluster_name="flask-sre-challenge-cluster",
        service_name="flask-sre-challenge-service"
    )
    
    print("Current Capacity Analysis:")
    print(json.dumps(analysis, indent=2))
    
    # Generate recommendations
    recs = recommendations.generate_recommendations(
        cluster_name="flask-sre-challenge-cluster",
        service_name="flask-sre-challenge-service"
    )
    
    print("\nCapacity Recommendations:")
    print(json.dumps(recs, indent=2))
