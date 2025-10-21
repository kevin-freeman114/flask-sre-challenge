import os
import logging
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, ValidationError
from dotenv import load_dotenv

# Import SRE components
from sre.slo_sli import sli_calculator
from sre.circuit_breaker import circuit_breaker, db_circuit_breaker, circuit_breaker_manager
from sre.dashboard import register_sre_blueprint

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:////tmp/flask_app.db')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

db = SQLAlchemy(app)


# Marshmallow schemas for validation
class UserSchema(Schema):
    name = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)
    email = fields.Email(required=True)

user_schema = UserSchema()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, name, email):
        self.name = name.strip()
        self.email = email.strip().lower()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# Health check endpoints
@app.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint with SRE monitoring"""
    start_time = time.time()
    status_code = 200
    
    try:
        # Test database connection with circuit breaker
        db_result = db_circuit_breaker.execute_query(
            lambda: db.session.execute('SELECT 1')
        )
        
        response_time = (time.time() - start_time) * 1000
        
        # Record SLI metrics
        sli_calculator.record_request('health', 200, response_time)
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'response_time_ms': response_time
        }), status_code
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        status_code = 503
        
        # Record SLI metrics for failure
        sli_calculator.record_request('health', status_code, response_time)
        
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'disconnected',
            'error': str(e),
            'response_time_ms': response_time
        }), status_code

@app.route('/health/ready', methods=['GET'])
def readiness_check():
    """Readiness check for Kubernetes/ECS"""
    try:
        db.session.execute('SELECT 1')
        return jsonify({'status': 'ready'}), 200
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return jsonify({'status': 'not ready', 'error': str(e)}), 503

@app.route('/health/live', methods=['GET'])
def liveness_check():
    """Liveness check for Kubernetes/ECS"""
    return jsonify({'status': 'alive'}), 200

# API endpoints with SRE monitoring
@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users as JSON with SRE monitoring"""
    start_time = time.time()
    status_code = 200
    
    try:
        # Use circuit breaker for database query
        users = db_circuit_breaker.execute_query(
            lambda: User.query.all()
        )
        
        response_time = (time.time() - start_time) * 1000
        
        # Record SLI metrics
        sli_calculator.record_request('api_users_get', status_code, response_time)
        
        return jsonify([user.to_dict() for user in users]), status_code
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        status_code = 500
        
        # Record SLI metrics for failure
        sli_calculator.record_request('api_users_get', status_code, response_time)
        
        logger.error(f"Error fetching users: {str(e)}")
        return jsonify({'error': 'Failed to fetch users'}), status_code

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user via API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate input
        try:
            validated_data = user_schema.load(data)
        except ValidationError as e:
            return jsonify({'error': 'Validation failed', 'details': e.messages}), 400
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=validated_data['email']).first()
        if existing_user:
            return jsonify({'error': 'User with this email already exists'}), 409
        
        # Create user
        user = User(validated_data['name'], validated_data['email'])
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"Created user: {user.email}")
        return jsonify(user.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating user: {str(e)}")
        return jsonify({'error': 'Failed to create user'}), 500

# Web interface routes
@app.route('/', methods=['GET'])
def index():
    """Main page with user form"""
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template('index.html', users=users)
    except Exception as e:
        logger.error(f"Error loading index page: {str(e)}")
        return render_template('index.html', users=[], error="Failed to load users")

@app.route('/user', methods=['POST'])
def create_user_web():
    """Create user via web form"""
    try:
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        
        if not name or not email:
            return render_template('index.html', 
                                 users=User.query.all(), 
                                 error="Name and email are required")
        
        # Validate email format
        try:
            user_schema.load({'name': name, 'email': email})
        except ValidationError as e:
            return render_template('index.html', 
                                 users=User.query.all(), 
                                 error=f"Invalid input: {', '.join(e.messages.get('email', []))}")
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email.lower()).first()
        if existing_user:
            return render_template('index.html', 
                                 users=User.query.all(), 
                                 error="User with this email already exists")
        
        user = User(name, email)
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"Created user via web: {user.email}")
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating user via web: {str(e)}")
        return render_template('index.html', 
                             users=User.query.all(), 
                             error="Failed to create user")

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

# Initialize database
def init_db():
    """Initialize database tables"""
    try:
        db.create_all()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

# Register SRE blueprint
register_sre_blueprint(app)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)

import os

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:////tmp/flask_app.db')

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db = SQLAlchemy(app)


class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100))
  email = db.Column(db.String(100))

  def __init__(self, name, email):
    self.name = name
    self.email = email


@app.route('/', methods=['GET'])
def index():
  return render_template('index.html', users=User.query.all())


@app.route('/user', methods=['POST'])
def user():
  u = User(request.form['name'], request.form['email'])
  db.session.add(u)
  db.session.commit()
  return redirect(url_for('index'))

if __name__ == '__main__':
  db.create_all()
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port, debug=True)
