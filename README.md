# Flask SRE Challenge - Production-Ready User Management System

A production-ready Flask application deployed on AWS with comprehensive SRE practices including monitoring, security, CI/CD, and infrastructure as code.

## 🚀 Live Application

**Application URL:** [Deployed via AWS ECS + ALB](http://your-alb-dns-name.us-east-1.elb.amazonaws.com)

**Health Check:** `/health`  
**API Documentation:** `/api/users` (GET/POST)

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Local Development](#local-development)
- [AWS Deployment](#aws-deployment)
- [Monitoring & Observability](#monitoring--observability)
- [Security](#security)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Next Steps for SRE Team](#next-steps-for-sre-team)

## ✨ Features

### Application Features
- **User Management**: Create and view users with email validation
- **REST API**: Full CRUD operations via JSON API
- **Health Checks**: Kubernetes/ECS-ready health endpoints
- **Input Validation**: Comprehensive data validation and sanitization
- **Error Handling**: Graceful error handling with proper HTTP status codes
- **Logging**: Structured logging with CloudWatch integration

### Infrastructure Features
- **Containerized**: Docker with multi-stage builds
- **AWS ECS**: Serverless container orchestration
- **RDS PostgreSQL**: Managed database with encryption
- **Application Load Balancer**: High availability and SSL termination
- **VPC**: Isolated network with public/private subnets
- **Auto Scaling**: ECS service auto-scaling
- **Infrastructure as Code**: Terraform for reproducible deployments

### DevOps Features
- **CI/CD Pipeline**: GitHub Actions for automated deployment
- **Monitoring**: CloudWatch metrics and alarms
- **Security**: Secrets management, input validation, security headers
- **Testing**: Comprehensive test suite with pytest
- **Documentation**: Detailed setup and operational guides

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Internet      │    │   CloudFront    │    │   Route 53      │
│   Users         │───▶│   CDN           │───▶│   DNS           │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │    │   Application   │    │   Application   │
│   Load Balancer │◀───│   Load Balancer │───▶│   Load Balancer │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ECS Service   │    │   ECS Service   │    │   ECS Service   │
│   (Container)   │    │   (Container)   │    │   (Container)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   RDS           │
                    │   PostgreSQL    │
                    │   (Encrypted)   │
                    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- Docker installed
- Terraform >= 1.0
- Python 3.11+

### 1. Clone and Setup
```bash
git clone <repository-url>
cd flask-sre-challenge
cp env.example .env
# Edit .env with your configuration
```

### 2. Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Start development server
python app.py
```

### 3. Docker Development
```bash
# Build and run with docker-compose
docker-compose up --build

# Access application at http://localhost
```

## 🏗️ AWS Deployment

### Automated Deployment (Recommended)
```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_ACCOUNT_ID=your-account-id

# Run deployment script
./deploy.sh
```

### Manual Deployment Steps

#### 1. Build and Push Docker Image
```bash
# Build image
docker build -t flask-sre-challenge .

# Tag for ECR
docker tag flask-sre-challenge:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/flask-sre-challenge:latest

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# Push image
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/flask-sre-challenge:latest
```

#### 2. Deploy Infrastructure
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

#### 3. Deploy Application
```bash
# Update ECS service to use new image
aws ecs update-service \
  --cluster flask-sre-challenge-cluster \
  --service flask-sre-challenge-service \
  --force-new-deployment
```

## 📊 Monitoring & Observability

### Health Checks
- **Liveness**: `GET /health/live` - Basic application health
- **Readiness**: `GET /health/ready` - Database connectivity check
- **Health**: `GET /health` - Comprehensive health status

### CloudWatch Metrics
- Application response times
- Error rates
- Database connection status
- ECS service metrics

### Logging
- Structured JSON logging
- CloudWatch Logs integration
- Request/response logging
- Error tracking

### Alarms
- High error rate (>5 errors/minute)
- High response time (>2 seconds)
- Low health check success rate (<90%)

## 🔒 Security

### Security Features
- **HTTPS**: SSL/TLS termination at ALB
- **Security Headers**: XSS protection, content type options, frame options
- **Input Validation**: Comprehensive data validation and sanitization
- **Secrets Management**: AWS Secrets Manager integration
- **Network Security**: VPC with private subnets, security groups
- **Database Security**: Encrypted RDS with private subnets

### Security Headers
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

## 📚 API Documentation

### Endpoints

#### Health Checks
- `GET /health` - Application health status with SRE metrics
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

#### User Management
- `GET /api/users` - List all users
- `POST /api/users` - Create a new user

#### SRE Dashboard & Monitoring
- `GET /sre/dashboard` - SRE dashboard data (JSON)
- `GET /sre/dashboard-ui` - SRE dashboard web interface
- `GET /sre/health` - System health status
- `GET /sre/metrics` - Performance metrics
- `GET /sre/capacity` - Capacity planning data
- `GET /sre/circuit-breakers` - Circuit breaker status
- `GET /sre/alerts` - Active alerts

#### Web Interface
- `GET /` - Main user management interface
- `POST /user` - Create user via web form

### API Examples

#### Create User
```bash
curl -X POST http://your-alb-dns/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'
```

#### Get Users
```bash
curl http://your-alb-dns/api/users
```

#### SRE Dashboard Access
```bash
# Get SRE dashboard data
curl http://your-alb-dns/sre/dashboard

# Check system health
curl http://your-alb-dns/sre/health

# Get performance metrics
curl http://your-alb-dns/sre/metrics

# Check circuit breaker status
curl http://your-alb-dns/sre/circuit-breakers

# Get active alerts
curl http://your-alb-dns/sre/alerts
```

#### SRE Dashboard Web Interface
```bash
# Access the SRE dashboard UI
open http://your-alb-dns/sre/dashboard-ui
```

## 🧪 Testing

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-flask

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html
```

### Test Coverage
- Unit tests for all endpoints
- Input validation tests
- Error handling tests
- Database integration tests
- Health check tests

## 🔧 SRE Features Implemented

### Service Level Objectives (SLOs) & Service Level Indicators (SLIs)
- **Availability SLO**: 99.9% uptime target
- **Latency SLO**: 95% of requests under 200ms
- **Error Rate SLO**: 99% success rate (1% error rate)
- **Data Freshness SLO**: 99.5% fresh data queries
- **Error Budget Tracking**: Real-time error budget consumption monitoring
- **SLI Calculation**: Automated SLI calculation and SLO evaluation

### Circuit Breaker Pattern
- **Database Circuit Breaker**: Protects against database failures
- **External Service Circuit Breaker**: Protects against external API failures
- **Configurable Thresholds**: Customizable failure thresholds and recovery timeouts
- **Circuit State Monitoring**: Real-time circuit breaker status tracking
- **Fallback Mechanisms**: Graceful degradation when circuits are open

### Comprehensive Monitoring & Observability
- **SRE Dashboard**: Real-time system health and performance monitoring
- **CloudWatch Integration**: AWS-native monitoring and alerting
- **Custom Metrics**: Application-specific metrics and SLI tracking
- **Health Checks**: Kubernetes/ECS-ready health endpoints
- **Performance Metrics**: Response time, throughput, and error rate tracking

### Capacity Planning & Auto-Scaling
- **Capacity Analysis**: Current resource utilization analysis
- **Growth Prediction**: Capacity needs prediction based on growth rates
- **Auto-Scaling Policies**: ECS service auto-scaling configuration
- **Resource Recommendations**: Automated capacity recommendations
- **Scaling Metrics**: CPU, memory, and custom metric-based scaling

### Chaos Engineering
- **Network Chaos**: Latency injection and network failure simulation
- **Infrastructure Chaos**: ECS service scaling and termination tests
- **Database Chaos**: Connection failure and performance degradation tests
- **Load Testing**: High concurrency and load simulation
- **Automated Experiments**: Orchestrated chaos engineering experiments

### Incident Response & Runbooks
- **Severity Levels**: P0-P3 incident classification
- **Response Procedures**: Detailed incident response workflows
- **Escalation Matrix**: Clear escalation paths and responsibilities
- **Communication Templates**: Standardized incident communication
- **Post-Mortem Process**: Structured post-incident analysis

### Security & Compliance
- **Input Validation**: Comprehensive data validation and sanitization
- **Security Headers**: XSS protection, content type options, frame options
- **Secrets Management**: AWS Secrets Manager integration
- **Network Security**: VPC with private subnets and security groups
- **Database Security**: Encrypted RDS with private network access

## 🎯 Next Steps for SRE Team

### Immediate Priorities (Week 1-2)

#### 1. **Production Hardening**
- [ ] **SSL Certificate**: Implement ACM certificate for HTTPS
- [ ] **Domain Setup**: Configure Route 53 with custom domain
- [ ] **Secrets Rotation**: Implement automated secret rotation
- [ ] **Database Backup**: Set up automated RDS backups with point-in-time recovery
- [ ] **Security Scanning**: Integrate container vulnerability scanning

#### 2. **Monitoring Enhancement**
- [ ] **APM Integration**: Add Application Performance Monitoring (New Relic/DataDog)
- [ ] **Custom Dashboards**: Create CloudWatch dashboards for key metrics
- [ ] **Alerting**: Set up PagerDuty integration for critical alerts
- [ ] **Log Aggregation**: Implement centralized logging with ELK stack
- [ ] **Synthetic Monitoring**: Add uptime monitoring with external checks

#### 3. **Scalability Improvements**
- [ ] **Auto Scaling**: Configure ECS service auto-scaling based on CPU/memory
- [ ] **Database Scaling**: Implement read replicas for database scaling
- [ ] **Caching**: Add Redis for session management and caching
- [ ] **CDN**: Implement CloudFront for static asset delivery
- [ ] **Load Testing**: Perform load testing to identify bottlenecks

### Medium-term Goals (Month 1-2)

#### 4. **High Availability**
- [ ] **Multi-AZ Deployment**: Ensure all resources are multi-AZ
- [ ] **Disaster Recovery**: Implement cross-region backup strategy
- [ ] **Circuit Breakers**: Add circuit breaker patterns for external dependencies
- [ ] **Graceful Degradation**: Implement fallback mechanisms
- [ ] **Chaos Engineering**: Regular chaos engineering exercises

#### 5. **Security Hardening**
- [ ] **WAF Integration**: Add AWS WAF for DDoS protection
- [ ] **Security Groups**: Implement least-privilege security group rules
- [ ] **IAM Roles**: Implement least-privilege IAM policies
- [ ] **Compliance**: Implement SOC 2/PCI compliance measures
- [ ] **Penetration Testing**: Regular security assessments

#### 6. **Operational Excellence**
- [ ] **Runbooks**: Create detailed operational runbooks
- [ ] **Incident Response**: Implement incident response procedures
- [ ] **Post-mortems**: Establish blameless post-mortem culture
- [ ] **Capacity Planning**: Implement capacity planning processes
- [ ] **Cost Optimization**: Regular cost reviews and optimization

### Long-term Vision (Month 3-6)

#### 7. **Advanced Monitoring**
- [ ] **Distributed Tracing**: Implement OpenTelemetry tracing
- [ ] **Machine Learning**: Add ML-based anomaly detection
- [ ] **Predictive Scaling**: Implement predictive auto-scaling
- [ ] **Business Metrics**: Track business KPIs alongside technical metrics
- [ ] **SLA/SLO Management**: Define and track service level objectives

#### 8. **Platform Evolution**
- [ ] **Kubernetes Migration**: Evaluate migration to EKS
- [ ] **Service Mesh**: Implement service mesh for microservices
- [ ] **GitOps**: Implement GitOps deployment model
- [ ] **Multi-cloud Strategy**: Evaluate multi-cloud deployment
- [ ] **Edge Computing**: Implement edge computing capabilities

#### 9. **Developer Experience**
- [ ] **Self-Service Platform**: Build self-service deployment platform
- [ ] **Feature Flags**: Implement feature flag management
- [ ] **A/B Testing**: Add A/B testing capabilities
- [ ] **Developer Tools**: Build internal developer tools
- [ ] **Documentation**: Comprehensive API and operational documentation

### Key Metrics to Track

#### Technical Metrics
- **Availability**: 99.9% uptime target
- **Response Time**: <200ms p95 response time
- **Error Rate**: <0.1% error rate
- **Throughput**: Requests per second capacity
- **Resource Utilization**: CPU/Memory usage patterns

#### Business Metrics
- **User Registration**: New user signup rate
- **API Usage**: API endpoint usage patterns
- **Performance Impact**: Business impact of performance issues
- **Cost per Transaction**: Infrastructure cost efficiency
- **Time to Recovery**: Mean time to recovery (MTTR)

### Risk Assessment

#### High Priority Risks
1. **Database Failure**: Implement automated failover and backups
2. **Security Breach**: Regular security audits and penetration testing
3. **Performance Degradation**: Proactive monitoring and capacity planning
4. **Data Loss**: Comprehensive backup and recovery procedures
5. **Compliance Violations**: Regular compliance audits and controls

#### Mitigation Strategies
- **Redundancy**: Multi-AZ deployment for all critical components
- **Monitoring**: Comprehensive monitoring with early warning systems
- **Automation**: Automated responses to common issues
- **Documentation**: Detailed runbooks and procedures
- **Training**: Regular team training on incident response

## 📞 Support & Contact

For questions or issues:
- **Documentation**: Check this README and inline code comments
- **Issues**: Create GitHub issues for bugs or feature requests
- **Monitoring**: Check CloudWatch dashboards for system status
- **Logs**: Review CloudWatch logs for application issues

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with ❤️ for the Balto SRE Challenge**

*This application demonstrates production-ready SRE practices including infrastructure as code, monitoring, security, CI/CD, and operational excellence.*