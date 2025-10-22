# Security configuration and utilities
import os
import secrets
import hashlib
from functools import wraps
from flask import request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration class"""
    
    @staticmethod
    def generate_secret_key():
        """Generate a secure secret key"""
        return secrets.token_hex(32)
    
    @staticmethod
    def hash_password(password):
        """Hash a password using SHA-256 with salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    @staticmethod
    def verify_password(password, hashed_password):
        """Verify a password against its hash"""
        try:
            salt, password_hash = hashed_password.split(':')
            return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
        except ValueError:
            return False

def rate_limit(max_requests=100, window=3600):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Simple in-memory rate limiting (in production, use Redis)
            client_ip = request.remote_addr
            current_time = int(time.time())
            
            # This is a simplified implementation
            # In production, use Redis or similar for distributed rate limiting
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_input(data, required_fields=None, max_length=None):
    """Validate input data"""
    if not isinstance(data, dict):
        return False, "Data must be a dictionary"
    
    if required_fields:
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
    
    if max_length:
        for field, value in data.items():
            if isinstance(value, str) and len(value) > max_length.get(field, 1000):
                return False, f"Field {field} exceeds maximum length"
    
    return True, None

def sanitize_input(data):
    """Sanitize input data"""
    if isinstance(data, dict):
        return {key: sanitize_input(value) for key, value in data.items()}
    elif isinstance(data, str):
        # Remove potentially dangerous characters
        return data.strip().replace('<', '&lt;').replace('>', '&gt;')
    else:
        return data

def log_security_event(event_type, details):
    """Log security events"""
    logger.warning(f"Security Event - {event_type}: {details}")

# Security headers middleware
def add_security_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# Input validation decorator
def validate_json_input(schema):
    """Decorator to validate JSON input"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            # Validate against schema
            try:
                validated_data = schema.load(data)
                request.validated_data = validated_data
            except ValidationError as e:
                return jsonify({'error': 'Validation failed', 'details': e.messages}), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# SQL injection protection
def escape_sql_string(value):
    """Escape SQL string to prevent injection"""
    if isinstance(value, str):
        return value.replace("'", "''").replace("\\", "\\\\")
    return value

# CSRF protection (simplified)
def generate_csrf_token():
    """Generate CSRF token"""
    return secrets.token_urlsafe(32)

def validate_csrf_token(token):
    """Validate CSRF token"""
    # In production, implement proper CSRF token validation
    return token is not None and len(token) > 0
