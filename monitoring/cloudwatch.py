# CloudWatch monitoring configuration
import boto3
import json
from datetime import datetime, timedelta

class CloudWatchMonitor:
    def __init__(self, region='us-east-1'):
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.namespace = 'FlaskSREChallenge'
    
    def put_metric(self, metric_name, value, unit='Count', dimensions=None):
        """Put a custom metric to CloudWatch"""
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.utcnow()
        }
        
        if dimensions:
            metric_data['Dimensions'] = dimensions
        
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
        except Exception as e:
            print(f"Failed to put metric {metric_name}: {e}")
    
    def create_alarm(self, alarm_name, metric_name, threshold, comparison_operator='GreaterThanThreshold'):
        """Create a CloudWatch alarm"""
        alarm_config = {
            'AlarmName': alarm_name,
            'ComparisonOperator': comparison_operator,
            'EvaluationPeriods': 2,
            'MetricName': metric_name,
            'Namespace': self.namespace,
            'Period': 300,
            'Statistic': 'Average',
            'Threshold': threshold,
            'ActionsEnabled': True,
            'AlarmActions': [],
            'AlarmDescription': f'Alarm for {metric_name}',
            'TreatMissingData': 'notBreaching'
        }
        
        try:
            self.cloudwatch.put_metric_alarm(**alarm_config)
            print(f"Created alarm: {alarm_name}")
        except Exception as e:
            print(f"Failed to create alarm {alarm_name}: {e}")
    
    def get_metric_statistics(self, metric_name, start_time=None, end_time=None, period=300):
        """Get metric statistics from CloudWatch"""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=1)
        if not end_time:
            end_time = datetime.utcnow()
        
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace=self.namespace,
                MetricName=metric_name,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Average', 'Maximum', 'Minimum', 'Sum']
            )
            return response['Datapoints']
        except Exception as e:
            print(f"Failed to get metric statistics for {metric_name}: {e}")
            return []

# Example usage and monitoring setup
def setup_monitoring():
    """Set up CloudWatch monitoring for the application"""
    monitor = CloudWatchMonitor()
    
    # Create alarms for key metrics
    monitor.create_alarm(
        'HighErrorRate',
        'ErrorCount',
        5,
        'GreaterThanThreshold'
    )
    
    monitor.create_alarm(
        'HighResponseTime',
        'ResponseTime',
        2.0,
        'GreaterThanThreshold'
    )
    
    monitor.create_alarm(
        'LowHealthCheckSuccess',
        'HealthCheckSuccess',
        0.9,
        'LessThanThreshold'
    )
    
    print("Monitoring setup completed")

if __name__ == '__main__':
    setup_monitoring()
