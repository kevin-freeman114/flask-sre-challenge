# SRE Runbooks and Incident Response Procedures

## 🚨 INCIDENT RESPONSE RUNBOOK

### SEVERITY LEVELS

#### P0 - Critical (Page Immediately)
- **Service Down**: Application completely unavailable
- **Data Loss**: Any data corruption or loss
- **Security Breach**: Suspected security incident
- **SLO Violation**: Error budget exhausted (>50% consumed)

**Response Time**: 15 minutes
**Escalation**: Immediate escalation to on-call engineer

#### P1 - High (Page within 1 hour)
- **Performance Degradation**: >50% increase in response time
- **Partial Outage**: Core functionality affected
- **Database Issues**: Connection problems or slow queries
- **High Error Rate**: >5% error rate

**Response Time**: 1 hour
**Escalation**: Escalate if not resolved in 2 hours

#### P2 - Medium (Page within 4 hours)
- **Minor Performance Issues**: <50% increase in response time
- **Non-Critical Features**: Secondary features affected
- **Monitoring Alerts**: Non-critical monitoring issues

**Response Time**: 4 hours
**Escalation**: Escalate if not resolved in 8 hours

#### P3 - Low (Page within 24 hours)
- **Documentation Issues**: Missing or incorrect documentation
- **Enhancement Requests**: Feature requests or improvements

**Response Time**: 24 hours
**Escalation**: Escalate if not resolved in 72 hours

### INCIDENT RESPONSE WORKFLOW

#### 1. Detection and Initial Response (0-15 minutes)
```bash
# Check application status
curl -f http://your-alb-dns/health

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace "FlaskSREChallenge" \
  --metric-name "ErrorCount" \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Check ECS service status
aws ecs describe-services \
  --cluster flask-sre-challenge-cluster \
  --services flask-sre-challenge-service
```

#### 2. Assessment and Communication (15-30 minutes)
- **Update Status Page**: Post incident status
- **Notify Stakeholders**: Send initial incident notification
- **Create Incident Channel**: Set up dedicated Slack channel
- **Document Timeline**: Start incident timeline

#### 3. Investigation and Resolution (30 minutes - 2 hours)
- **Check Logs**: Review CloudWatch logs for errors
- **Database Check**: Verify RDS connectivity and performance
- **Infrastructure Check**: Verify ECS, ALB, and VPC status
- **Application Check**: Review application metrics and traces

#### 4. Resolution and Post-Incident (2+ hours)
- **Implement Fix**: Deploy resolution
- **Verify Resolution**: Confirm service restoration
- **Communicate Resolution**: Update stakeholders
- **Post-Mortem**: Schedule post-incident review

### COMMON INCIDENT SCENARIOS

#### Scenario 1: Application Completely Down
**Symptoms**: 5xx errors, health checks failing, no response

**Immediate Actions**:
1. Check ALB target group health
2. Verify ECS service status
3. Check RDS connectivity
4. Review recent deployments

**Commands**:
```bash
# Check ALB health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups --names flask-sre-challenge-tg --query 'TargetGroups[0].TargetGroupArn' --output text)

# Check ECS service
aws ecs describe-services \
  --cluster flask-sre-challenge-cluster \
  --services flask-sre-challenge-service

# Check RDS
aws rds describe-db-instances \
  --db-instance-identifier flask-sre-challenge-db
```

#### Scenario 2: High Error Rate
**Symptoms**: Error rate >5%, some requests failing

**Immediate Actions**:
1. Check application logs for error patterns
2. Verify database performance
3. Check for recent code changes
4. Monitor resource utilization

**Commands**:
```bash
# Check error logs
aws logs filter-log-events \
  --log-group-name "/ecs/flask-sre-challenge" \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000

# Check database performance
aws rds describe-db-instances \
  --db-instance-identifier flask-sre-challenge-db \
  --query 'DBInstances[0].DBInstanceStatus'
```

#### Scenario 3: Performance Degradation
**Symptoms**: High response times, slow database queries

**Immediate Actions**:
1. Check database performance metrics
2. Review application performance
3. Check for resource constraints
4. Analyze query patterns

**Commands**:
```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace "AWS/RDS" \
  --metric-name "DatabaseConnections" \
  --dimensions Name=DBInstanceIdentifier,Value=flask-sre-challenge-db \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### ESCALATION PROCEDURES

#### Level 1: On-Call Engineer
- **Primary**: Current on-call engineer
- **Responsibilities**: Initial response, basic troubleshooting
- **Escalation Time**: 30 minutes for P0, 1 hour for P1

#### Level 2: Senior Engineer
- **Primary**: Senior SRE or Backend Engineer
- **Responsibilities**: Complex troubleshooting, infrastructure changes
- **Escalation Time**: 1 hour for P0, 2 hours for P1

#### Level 3: Engineering Manager
- **Primary**: Engineering Manager or Staff Engineer
- **Responsibilities**: Major decisions, external communication
- **Escalation Time**: 2 hours for P0, 4 hours for P1

#### Level 4: Director/VP Engineering
- **Primary**: Director of Engineering or VP
- **Responsibilities**: Business impact decisions, customer communication
- **Escalation Time**: 4 hours for P0, 8 hours for P1

### COMMUNICATION TEMPLATES

#### Initial Incident Notification
```
🚨 INCIDENT ALERT - P[0/1/2] - [Service Name]

**Status**: Investigating
**Impact**: [Description of impact]
**Start Time**: [Timestamp]
**Affected Systems**: [List of affected systems]

**Next Update**: [Time for next update]

Incident Channel: #incident-[timestamp]
```

#### Status Update
```
📊 INCIDENT UPDATE - P[0/1/2] - [Service Name]

**Status**: [Investigating/Identified/Monitoring/Resolved]
**Impact**: [Updated impact description]
**Root Cause**: [If identified]
**ETA**: [Estimated time to resolution]

**Actions Taken**:
- [Action 1]
- [Action 2]

**Next Update**: [Time for next update]
```

#### Resolution Notification
```
✅ INCIDENT RESOLVED - P[0/1/2] - [Service Name]

**Status**: Resolved
**Resolution Time**: [Total incident duration]
**Root Cause**: [Final root cause]
**Resolution**: [How it was fixed]

**Post-Mortem**: Scheduled for [Date/Time]
```

### MONITORING AND ALERTING

#### Critical Alerts (P0)
- Service availability < 99%
- Error rate > 5%
- Database connection failures
- Circuit breaker open

#### Warning Alerts (P1)
- Response time > 2 seconds
- CPU utilization > 80%
- Memory utilization > 85%
- Database slow queries

#### Info Alerts (P2)
- Deployment notifications
- Configuration changes
- Scheduled maintenance

### POST-INCIDENT PROCESS

#### Post-Mortem Requirements
1. **Timeline**: Detailed incident timeline
2. **Root Cause**: Technical root cause analysis
3. **Impact**: Business and technical impact
4. **Actions**: Immediate and long-term actions
5. **Lessons Learned**: Key takeaways
6. **Prevention**: Steps to prevent recurrence

#### Post-Mortem Template
```markdown
# Post-Mortem: [Incident Title]

## Summary
[Brief summary of the incident]

## Timeline
- [Time]: [Event]
- [Time]: [Event]

## Root Cause
[Technical root cause]

## Impact
- **Users Affected**: [Number]
- **Duration**: [Time]
- **Business Impact**: [Description]

## Actions Taken
- [Action 1]
- [Action 2]

## Action Items
- [ ] [Action item 1] - [Owner] - [Due date]
- [ ] [Action item 2] - [Owner] - [Due date]

## Lessons Learned
[Key takeaways]
```

### EMERGENCY CONTACTS

#### On-Call Rotation
- **Primary**: [Name] - [Phone] - [Slack]
- **Secondary**: [Name] - [Phone] - [Slack]
- **Manager**: [Name] - [Phone] - [Slack]

#### External Contacts
- **AWS Support**: [Case ID] - [Phone]
- **Database Vendor**: [Contact]
- **Monitoring Vendor**: [Contact]

### USEFUL COMMANDS

#### Application Health
```bash
# Health check
curl -f http://your-alb-dns/health

# Detailed health
curl -f http://your-alb-dns/health | jq

# API status
curl -f http://your-alb-dns/api/users
```

#### Infrastructure Status
```bash
# ECS service status
aws ecs describe-services --cluster flask-sre-challenge-cluster --services flask-sre-challenge-service

# ALB health
aws elbv2 describe-target-health --target-group-arn [TG_ARN]

# RDS status
aws rds describe-db-instances --db-instance-identifier flask-sre-challenge-db
```

#### Logs and Metrics
```bash
# Recent logs
aws logs filter-log-events --log-group-name "/ecs/flask-sre-challenge" --start-time $(date -d '1 hour ago' +%s)000

# Error logs
aws logs filter-log-events --log-group-name "/ecs/flask-sre-challenge" --filter-pattern "ERROR"

# Metrics
aws cloudwatch get-metric-statistics --namespace "FlaskSREChallenge" --metric-name "ErrorCount" --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Sum
```
