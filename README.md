# Flask SRE Challenge

A Flask application with user management functionality, deployed on AWS with monitoring and SRE practices.

## Application

**URL:** [AWS ECS + ALB](http://your-alb-dns-name.us-east-1.elb.amazonaws.com)

**Health Check:** `/health`  
**API:** `/api/users` (GET/POST)

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Local Development](#local-development)
- [AWS Deployment](#aws-deployment)
- [Monitoring](#monitoring)
- [Security](#security)
- [API Documentation](#api-documentation)
- [Testing](#testing)

## Features

### Application
- User management with email validation
- REST API for CRUD operations
- Health check endpoints
- Input validation and error handling
- Structured logging

### Infrastructure
- Docker containerization
- AWS ECS deployment
- RDS PostgreSQL database
- Application Load Balancer
- VPC with public/private subnets
- Auto scaling
- Terraform infrastructure as code

### DevOps
- GitHub Actions CI/CD
- CloudWatch monitoring
- Security best practices
- Comprehensive testing

## Architecture

```
Internet → ALB → ECS Fargate → RDS PostgreSQL
```

## Quick Start

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
python main_app.py
```

### 3. Docker Development
```bash
# Build and run with docker-compose
docker-compose up --build

# Access application at http://localhost
```

## AWS Deployment

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

## Security

- HTTPS with SSL/TLS termination at ALB
- Security headers for XSS protection
- Input validation and sanitization
- AWS Secrets Manager integration
- VPC with private subnets
- Encrypted RDS database

## API Documentation

### Endpoints

- `GET /health` - Health check
- `GET /api/users` - List all users
- `POST /api/users` - Create a new user
- `GET /` - Main user interface
- `POST /user` - Create user via web form

### Examples

Create user:
```bash
curl -X POST http://your-alb-dns/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'
```

Get users:
```bash
curl http://your-alb-dns/api/users
```

## Testing

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

## SRE Features

- Service Level Objectives (SLOs) and Indicators (SLIs)
- Circuit breaker pattern for resilience
- Comprehensive monitoring and observability
- Capacity planning and auto-scaling
- Chaos engineering for resilience testing
- Incident response procedures
- Security and compliance measures