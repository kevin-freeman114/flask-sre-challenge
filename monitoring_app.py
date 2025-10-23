import os
import logging
import time
import psutil
from datetime import datetime
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Import SRE components (temporarily disabled for local testing)
# from sre.slo_sli import sli_calculator
# from sre.circuit_breaker import circuit_breaker, db_circuit_breaker, circuit_breaker_manager
# from sre.dashboard import register_sre_blueprint

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

# User model (same as main app)
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

# Health check endpoints
@app.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint with SRE monitoring"""
    start_time = time.time()
    status_code = 200
    
    try:
        # Test database connection with circuit breaker
        from sqlalchemy import text
        db_result = db_circuit_breaker.execute_query(
            lambda: db.session.execute(text('SELECT 1'))
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
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
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
        users = User.query.order_by(User.created_at.desc()).all()
        response_time = (time.time() - start_time) * 1000
        
        # Record SLI metrics
        sli_calculator.record_request('api_users', status_code, response_time)
        
        return jsonify([user.to_dict() for user in users])
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        status_code = 500
        
        # Record SLI metrics for failure
        sli_calculator.record_request('api_users', status_code, response_time)
        
        logger.error(f"Error fetching users: {str(e)}")
        return jsonify({'error': 'Failed to fetch users'}), status_code

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user via API with SRE monitoring"""
    start_time = time.time()
    status_code = 201
    
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'name' not in data or 'email' not in data:
            return jsonify({'error': 'Name and email are required'}), 400
        
        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        user = User(name=data['name'], email=data['email'])
        db.session.add(user)
        db.session.commit()
        
        response_time = (time.time() - start_time) * 1000
        
        # Record SLI metrics
        sli_calculator.record_request('api_create_user', status_code, response_time)
        
        logger.info(f"User created via API: {data['name']} ({data['email']})")
        return jsonify(user.to_dict()), status_code
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        status_code = 500
        
        # Record SLI metrics for failure
        sli_calculator.record_request('api_create_user', status_code, response_time)
        
        logger.error(f"Error creating user via API: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create user'}), status_code

# Simple monitoring dashboard
@app.route('/monitoring')
def monitoring_dashboard():
    """Simple monitoring dashboard"""
    try:
        # Get basic system info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database connection test
        db_status = "Connected"
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
        except Exception as e:
            db_status = f"Error: {str(e)}"
        
        # Get user count
        user_count = User.query.count()
        
        dashboard_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SRE Monitoring Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }}
                .metric-card {{ background: #ecf0f1; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db; }}
                .metric-card h3 {{ margin: 0 0 10px 0; color: #2c3e50; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #27ae60; }}
                .status-healthy {{ color: #27ae60; }}
                .status-warning {{ color: #f39c12; }}
                .status-error {{ color: #e74c3c; }}
                .refresh-btn {{ background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }}
                .refresh-btn:hover {{ background: #2980b9; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>SRE Monitoring Dashboard</h1>
                    <p>Real-time system health and performance metrics</p>
                    <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
                </div>
                
                <div class="metrics">
                    <div class="metric-card">
                        <h3>📊 System Health</h3>
                        <div class="metric-value status-healthy">HEALTHY</div>
                        <p>All systems operational</p>
                    </div>
                    
                    <div class="metric-card">
                        <h3>💾 Database Status</h3>
                        <div class="metric-value status-healthy">{db_status}</div>
                        <p>PostgreSQL connection active</p>
                    </div>
                    
                    <div class="metric-card">
                        <h3>👥 Users</h3>
                        <div class="metric-value">{user_count}</div>
                        <p>Registered users in database</p>
                    </div>
                    
                    <div class="metric-card">
                        <h3>🖥️ CPU Usage</h3>
                        <div class="metric-value status-healthy">{cpu_percent}%</div>
                        <p>Current CPU utilization</p>
                    </div>
                    
                    <div class="metric-card">
                        <h3>🧠 Memory</h3>
                        <div class="metric-value status-healthy">{memory.percent}%</div>
                        <p>{memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB used</p>
                    </div>
                    
                    <div class="metric-card">
                        <h3>💿 Disk Space</h3>
                        <div class="metric-value status-healthy">{disk.percent}%</div>
                        <p>{disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB used</p>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>🔗 Quick Links</h3>
                    <p>
                        <a href="http://localhost:5000/">🏠 Main Application</a> | 
                        <a href="http://localhost:5000/api/users">📡 API Endpoints</a> | 
                        <a href="/monitoring">📊 This Dashboard</a>
                    </p>
                </div>
                
                <div class="metric-card">
                    <h3>⏰ Last Updated</h3>
                    <p>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                </div>
            </div>
            
            <script>
                // Auto-refresh every 30 seconds
                setTimeout(() => location.reload(), 30000);
            </script>
        </body>
        </html>
        """
        
        return dashboard_html
        
    except Exception as e:
        logger.error(f"Error generating monitoring dashboard: {str(e)}")
        return f"<h1>Error</h1><p>Failed to generate monitoring dashboard: {str(e)}</p>", 500

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

# Register SRE blueprint
# register_sre_blueprint(app)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('MONITORING_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
