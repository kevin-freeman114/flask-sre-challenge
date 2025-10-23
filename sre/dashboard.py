# SRE Dashboard and Metrics System
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import boto3
from flask import Blueprint, jsonify, render_template_string

logger = logging.getLogger(__name__)

# Import SRE modules
from sre.slo_sli import sre_dashboard, sli_calculator
from sre.circuit_breaker import circuit_breaker_manager
from sre.capacity_planning import CapacityPlanner, CapacityRecommendations

# Create SRE blueprint
sre_bp = Blueprint('sre', __name__, url_prefix='/sre')

class SREDashboardMetrics:
    """SRE Dashboard metrics collector"""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.ecs = boto3.client('ecs')
        self.rds = boto3.client('rds')
        self.capacity_planner = CapacityPlanner()
        self.capacity_recommendations = CapacityRecommendations()
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        health = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'HEALTHY',
            'components': {},
            'alerts': [],
            'metrics': {}
        }
        
        try:
            # Check ECS service health
            ecs_health = self._check_ecs_health()
            health['components']['ecs'] = ecs_health
            
            # Check RDS health
            rds_health = self._check_rds_health()
            health['components']['rds'] = rds_health
            
            # Check ALB health
            alb_health = self._check_alb_health()
            health['components']['alb'] = alb_health
            
            # Check circuit breakers
            circuit_health = self._check_circuit_breakers()
            health['components']['circuit_breakers'] = circuit_health
            
            # Determine overall status
            component_statuses = [comp.get('status', 'UNKNOWN') for comp in health['components'].values()]
            if 'CRITICAL' in component_statuses:
                health['overall_status'] = 'CRITICAL'
            elif 'DEGRADED' in component_statuses:
                health['overall_status'] = 'DEGRADED'
            
            # Collect alerts
            health['alerts'] = self._collect_alerts(health['components'])
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            health['overall_status'] = 'ERROR'
            health['error'] = str(e)
        
        return health
    
    def _check_ecs_health(self) -> Dict[str, Any]:
        """Check ECS service health"""
        try:
            service_info = self.ecs.describe_services(
                cluster='flask-sre-challenge-cluster',
                services=['flask-sre-challenge-service']
            )
            
            service = service_info['services'][0]
            desired_count = service['desiredCount']
            running_count = service['runningCount']
            
            status = 'HEALTHY'
            if running_count < desired_count:
                status = 'DEGRADED'
            if running_count == 0:
                status = 'CRITICAL'
            
            return {
                'status': status,
                'desired_count': desired_count,
                'running_count': running_count,
                'pending_count': service['pendingCount'],
                'deployments': len(service['deployments'])
            }
            
        except Exception as e:
            logger.error(f"Failed to check ECS health: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def _check_rds_health(self) -> Dict[str, Any]:
        """Check RDS health"""
        try:
            db_info = self.rds.describe_db_instances(
                DBInstanceIdentifier='flask-sre-challenge-db'
            )
            
            db_instance = db_info['DBInstances'][0]
            status = db_instance['DBInstanceStatus']
            
            health_status = 'HEALTHY'
            if status != 'available':
                health_status = 'DEGRADED'
            
            return {
                'status': health_status,
                'db_status': status,
                'instance_class': db_instance['DBInstanceClass'],
                'allocated_storage': db_instance['AllocatedStorage'],
                'multi_az': db_instance['MultiAZ']
            }
            
        except Exception as e:
            logger.error(f"Failed to check RDS health: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def _check_alb_health(self) -> Dict[str, Any]:
        """Check ALB health"""
        try:
            elbv2 = boto3.client('elbv2')
            
            # Get load balancer info
            lb_response = elbv2.describe_load_balancers(
                Names=['flask-sre-challenge-alb']
            )
            
            if not lb_response['LoadBalancers']:
                return {'status': 'ERROR', 'error': 'Load balancer not found'}
            
            lb = lb_response['LoadBalancers'][0]
            
            # Get target group health
            tg_response = elbv2.describe_target_groups(
                Names=['flask-sre-challenge-tg']
            )
            
            if not tg_response['TargetGroups']:
                return {'status': 'ERROR', 'error': 'Target group not found'}
            
            tg_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
            
            health_response = elbv2.describe_target_health(
                TargetGroupArn=tg_arn
            )
            
            healthy_targets = sum(1 for target in health_response['TargetHealthDescriptions'] 
                                if target['TargetHealth']['State'] == 'healthy')
            total_targets = len(health_response['TargetHealthDescriptions'])
            
            status = 'HEALTHY'
            if healthy_targets < total_targets:
                status = 'DEGRADED'
            if healthy_targets == 0:
                status = 'CRITICAL'
            
            return {
                'status': status,
                'healthy_targets': healthy_targets,
                'total_targets': total_targets,
                'lb_state': lb['State']['Code']
            }
            
        except Exception as e:
            logger.error(f"Failed to check ALB health: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def _check_circuit_breakers(self) -> Dict[str, Any]:
        """Check circuit breaker status"""
        try:
            states = circuit_breaker_manager.get_all_states()
            open_circuits = circuit_breaker_manager.get_open_circuits()
            critical_circuits = circuit_breaker_manager.get_critical_circuits()
            
            status = 'HEALTHY'
            if critical_circuits:
                status = 'CRITICAL'
            elif open_circuits:
                status = 'DEGRADED'
            
            return {
                'status': status,
                'total_circuits': len(states),
                'open_circuits': len(open_circuits),
                'critical_circuits': len(critical_circuits),
                'circuit_states': states
            }
            
        except Exception as e:
            logger.error(f"Failed to check circuit breakers: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def _collect_alerts(self, components: Dict[str, Any]) -> List[Dict[str, str]]:
        """Collect alerts from all components"""
        alerts = []
        
        for component_name, component_data in components.items():
            if component_data.get('status') == 'CRITICAL':
                alerts.append({
                    'severity': 'CRITICAL',
                    'component': component_name,
                    'message': f'{component_name} is in CRITICAL state',
                    'timestamp': datetime.utcnow().isoformat()
                })
            elif component_data.get('status') == 'DEGRADED':
                alerts.append({
                    'severity': 'WARNING',
                    'component': component_name,
                    'message': f'{component_name} is in DEGRADED state',
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        return alerts
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the dashboard"""
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'time_range': '1 hour',
            'metrics': {}
        }
        
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            # Get application metrics
            app_metrics = self._get_application_metrics(start_time, end_time)
            metrics['metrics']['application'] = app_metrics
            
            # Get infrastructure metrics
            infra_metrics = self._get_infrastructure_metrics(start_time, end_time)
            metrics['metrics']['infrastructure'] = infra_metrics
            
            # Get business metrics
            business_metrics = self._get_business_metrics(start_time, end_time)
            metrics['metrics']['business'] = business_metrics
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            metrics['error'] = str(e)
        
        return metrics
    
    def _get_application_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get application-level metrics"""
        try:
            # Request count
            request_count_response = self.cloudwatch.get_metric_statistics(
                Namespace='FlaskSREChallenge',
                MetricName='RequestCount',
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )
            
            # Error count
            error_count_response = self.cloudwatch.get_metric_statistics(
                Namespace='FlaskSREChallenge',
                MetricName='ErrorCount',
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )
            
            # Response time
            response_time_response = self.cloudwatch.get_metric_statistics(
                Namespace='FlaskSREChallenge',
                MetricName='ResponseTime',
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            return {
                'request_count': self._sum_datapoints(request_count_response.get('Datapoints', [])),
                'error_count': self._sum_datapoints(error_count_response.get('Datapoints', [])),
                'avg_response_time': self._avg_datapoints(response_time_response.get('Datapoints', []))
            }
            
        except Exception as e:
            logger.error(f"Failed to get application metrics: {e}")
            return {'error': str(e)}
    
    def _get_infrastructure_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get infrastructure metrics"""
        try:
            # ECS CPU utilization
            ecs_cpu_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ECS',
                MetricName='CPUUtilization',
                Dimensions=[
                    {'Name': 'ClusterName', 'Value': 'flask-sre-challenge-cluster'},
                    {'Name': 'ServiceName', 'Value': 'flask-sre-challenge-service'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            # RDS CPU utilization
            rds_cpu_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': 'flask-sre-challenge-db'}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            return {
                'ecs_cpu_utilization': self._avg_datapoints(ecs_cpu_response.get('Datapoints', [])),
                'rds_cpu_utilization': self._avg_datapoints(rds_cpu_response.get('Datapoints', []))
            }
            
        except Exception as e:
            logger.error(f"Failed to get infrastructure metrics: {e}")
            return {'error': str(e)}
    
    def _get_business_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get business metrics"""
        try:
            # User registrations (simplified - in production, this would be tracked)
            return {
                'user_registrations': 0,  # Would be tracked from application logs
                'api_calls': 0,  # Would be tracked from application logs
                'active_users': 0  # Would be tracked from application logs
            }
            
        except Exception as e:
            logger.error(f"Failed to get business metrics: {e}")
            return {'error': str(e)}
    
    def _sum_datapoints(self, datapoints: List[Dict]) -> float:
        """Sum datapoints"""
        return sum(dp.get('Sum', 0) for dp in datapoints)
    
    def _avg_datapoints(self, datapoints: List[Dict]) -> float:
        """Average datapoints"""
        if not datapoints:
            return 0.0
        return sum(dp.get('Average', 0) for dp in datapoints) / len(datapoints)

# Initialize metrics collector
sre_metrics = SREDashboardMetrics()

# SRE Dashboard Routes
@sre_bp.route('/dashboard')
def sre_dashboard_view():
    """SRE Dashboard main view"""
    dashboard_data = sre_dashboard.get_dashboard_data()
    system_health = sre_metrics.get_system_health()
    performance_metrics = sre_metrics.get_performance_metrics()
    
    return jsonify({
        'dashboard': dashboard_data,
        'system_health': system_health,
        'performance_metrics': performance_metrics
    })

@sre_bp.route('/health')
def sre_health():
    """SRE system health endpoint"""
    health = sre_metrics.get_system_health()
    return jsonify(health)

@sre_bp.route('/metrics')
def sre_metrics_endpoint():
    """SRE metrics endpoint"""
    metrics = sre_metrics.get_performance_metrics()
    return jsonify(metrics)

@sre_bp.route('/capacity')
def sre_capacity():
    """SRE capacity planning endpoint"""
    try:
        analysis = sre_metrics.capacity_planner.analyze_current_capacity(
            cluster_name='flask-sre-challenge-cluster',
            service_name='flask-sre-challenge-service'
        )
        
        recommendations = sre_metrics.capacity_recommendations.generate_recommendations(
            cluster_name='flask-sre-challenge-cluster',
            service_name='flask-sre-challenge-service'
        )
        
        return jsonify({
            'capacity_analysis': analysis,
            'recommendations': recommendations
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@sre_bp.route('/circuit-breakers')
def circuit_breakers_status():
    """Circuit breakers status endpoint"""
    states = circuit_breaker_manager.get_all_states()
    open_circuits = circuit_breaker_manager.get_open_circuits()
    critical_circuits = circuit_breaker_manager.get_critical_circuits()
    
    return jsonify({
        'circuit_breakers': states,
        'open_circuits': open_circuits,
        'critical_circuits': critical_circuits,
        'summary': {
            'total': len(states),
            'open': len(open_circuits),
            'critical': len(critical_circuits)
        }
    })

@sre_bp.route('/alerts')
def sre_alerts():
    """SRE alerts endpoint"""
    system_health = sre_metrics.get_system_health()
    alerts = system_health.get('alerts', [])
    
    # Add SLO alerts
    slo_data = sre_dashboard.get_dashboard_data()
    slo_alerts = slo_data.get('alerts', [])
    
    all_alerts = alerts + [{'severity': 'INFO', 'component': 'SLO', 'message': alert} for alert in slo_alerts]
    
    return jsonify({
        'alerts': all_alerts,
        'total_alerts': len(all_alerts),
        'critical_alerts': len([a for a in all_alerts if a.get('severity') == 'CRITICAL']),
        'warning_alerts': len([a for a in all_alerts if a.get('severity') == 'WARNING'])
    })

# SRE Dashboard HTML Template
SRE_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SRE Dashboard - Flask SRE Challenge</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-healthy { color: #27ae60; }
        .status-degraded { color: #f39c12; }
        .status-critical { color: #e74c3c; }
        .alert { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .alert-critical { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .alert-warning { background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
        .refresh-btn { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SRE Dashboard</h1>
            <p>Flask SRE Challenge - Production Monitoring</p>
            <button class="refresh-btn" onclick="refreshDashboard()">Refresh</button>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>System Health</h3>
                <div id="system-health">Loading...</div>
            </div>
            
            <div class="metric-card">
                <h3>SLO Status</h3>
                <div id="slo-status">Loading...</div>
            </div>
            
            <div class="metric-card">
                <h3>Circuit Breakers</h3>
                <div id="circuit-breakers">Loading...</div>
            </div>
            
            <div class="metric-card">
                <h3>Performance Metrics</h3>
                <div id="performance-metrics">Loading...</div>
            </div>
            
            <div class="metric-card">
                <h3>Alerts</h3>
                <div id="alerts">Loading...</div>
            </div>
            
            <div class="metric-card">
                <h3>Capacity Planning</h3>
                <div id="capacity-planning">Loading...</div>
            </div>
        </div>
    </div>
    
    <script>
        function refreshDashboard() {
            loadSystemHealth();
            loadSLOStatus();
            loadCircuitBreakers();
            loadPerformanceMetrics();
            loadAlerts();
            loadCapacityPlanning();
        }
        
        function loadSystemHealth() {
            fetch('/sre/health')
                .then(response => response.json())
                .then(data => {
                    const status = data.overall_status;
                    const statusClass = 'status-' + status.toLowerCase();
                    document.getElementById('system-health').innerHTML = 
                        `<div class="${statusClass}"><strong>Status:</strong> ${status}</div>
                         <div><strong>Components:</strong> ${Object.keys(data.components).length}</div>
                         <div><strong>Alerts:</strong> ${data.alerts.length}</div>`;
                });
        }
        
        function loadSLOStatus() {
            fetch('/sre/dashboard')
                .then(response => response.json())
                .then(data => {
                    const slos = data.dashboard.slos;
                    let html = '';
                    for (const [name, slo] of Object.entries(slos)) {
                        const statusClass = slo.status === 'PASS' ? 'status-healthy' : 'status-critical';
                        html += `<div class="${statusClass}"><strong>${name}:</strong> ${slo.sli_value.toFixed(2)}% (target: ${slo.slo_target}%)</div>`;
                    }
                    document.getElementById('slo-status').innerHTML = html;
                });
        }
        
        function loadCircuitBreakers() {
            fetch('/sre/circuit-breakers')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('circuit-breakers').innerHTML = 
                        `<div><strong>Total:</strong> ${data.summary.total}</div>
                         <div><strong>Open:</strong> ${data.summary.open}</div>
                         <div><strong>Critical:</strong> ${data.summary.critical}</div>`;
                });
        }
        
        function loadPerformanceMetrics() {
            fetch('/sre/metrics')
                .then(response => response.json())
                .then(data => {
                    const app = data.metrics.application;
                    document.getElementById('performance-metrics').innerHTML = 
                        `<div><strong>Requests:</strong> ${app.request_count || 0}</div>
                         <div><strong>Errors:</strong> ${app.error_count || 0}</div>
                         <div><strong>Avg Response Time:</strong> ${(app.avg_response_time || 0).toFixed(3)}s</div>`;
                });
        }
        
        function loadAlerts() {
            fetch('/sre/alerts')
                .then(response => response.json())
                .then(data => {
                    let html = '';
                    data.alerts.forEach(alert => {
                        const alertClass = alert.severity.toLowerCase() === 'critical' ? 'alert-critical' : 'alert-warning';
                        html += `<div class="alert ${alertClass}"><strong>${alert.severity}:</strong> ${alert.message}</div>`;
                    });
                    if (html === '') html = '<div>No active alerts</div>';
                    document.getElementById('alerts').innerHTML = html;
                });
        }
        
        function loadCapacityPlanning() {
            fetch('/sre/capacity')
                .then(response => response.json())
                .then(data => {
                    const recs = data.recommendations.recommendations;
                    let html = '';
                    recs.forEach(rec => {
                        html += `<div><strong>${rec.component}:</strong> ${rec.recommendation}</div>`;
                    });
                    if (html === '') html = '<div>No recommendations</div>';
                    document.getElementById('capacity-planning').innerHTML = html;
                });
        }
        
        // Load dashboard on page load
        refreshDashboard();
        
        // Auto-refresh every 30 seconds
        setInterval(refreshDashboard, 30000);
    </script>
</body>
</html>
"""

@sre_bp.route('/dashboard-ui')
def sre_dashboard_ui():
    """SRE Dashboard UI"""
    return render_template_string(SRE_DASHBOARD_TEMPLATE)

# Export the blueprint for use in the main app
def register_sre_blueprint(app):
    """Register SRE blueprint with Flask app"""
    app.register_blueprint(sre_bp)
    logger.info("SRE dashboard blueprint registered")
