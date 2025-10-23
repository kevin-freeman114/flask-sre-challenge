import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, ValidationError
from dotenv import load_dotenv

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
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Initialize database
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, name, email):
        self.name = name
        self.email = email

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# User schema for validation
class UserSchema(Schema):
    name = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)
    email = fields.Email(required=True)

user_schema = UserSchema()

# Routes
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
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            return render_template('index.html', 
                                 users=User.query.all(), 
                                 error="Email already exists")
        
        user = User(name=name, email=email)
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"User created: {name} ({email})")
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        db.session.rollback()
        return render_template('index.html', 
                             users=User.query.all(), 
                             error="Failed to create user")

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users as JSON"""
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        return jsonify([user.to_dict() for user in users])
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user via API"""
    try:
        data = request.get_json()
        
        # Validate input
        errors = user_schema.validate(data)
        if errors:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        
        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        user = User(name=data['name'], email=data['email'])
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"User created via API: {data['name']} ({data['email']})")
        return jsonify(user.to_dict()), 201
        
    except Exception as e:
        logger.error(f"Error creating user via API: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create user'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# Initialize database tables
def init_db():
    """Initialize database tables"""
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Add sample data if no users exist
            if User.query.count() == 0:
                sample_users = [
                    User('John Doe', 'john@example.com'),
                    User('Jane Smith', 'jane@example.com'),
                    User('Bob Johnson', 'bob@example.com')
                ]
                for user in sample_users:
                    db.session.add(user)
                db.session.commit()
                logger.info("Sample data added successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
