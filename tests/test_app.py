import pytest
import json
from main_app import app, db, User

@pytest.fixture
def client():
    """Create a test client"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert data['database'] == 'connected'

def test_readiness_check(client):
    """Test readiness check endpoint"""
    response = client.get('/health/ready')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'ready'

def test_liveness_check(client):
    """Test liveness check endpoint"""
    response = client.get('/health/live')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'alive'

def test_get_users_empty(client):
    """Test getting users when none exist"""
    response = client.get('/api/users')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data == []

def test_create_user_api(client):
    """Test creating a user via API"""
    user_data = {
        'name': 'John Doe',
        'email': 'john@example.com'
    }
    
    response = client.post('/api/users', 
                          data=json.dumps(user_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    
    data = json.loads(response.data)
    assert data['name'] == 'John Doe'
    assert data['email'] == 'john@example.com'
    assert 'id' in data
    assert 'created_at' in data

def test_create_user_duplicate_email(client):
    """Test creating a user with duplicate email"""
    user_data = {
        'name': 'John Doe',
        'email': 'john@example.com'
    }
    
    # Create first user
    client.post('/api/users', 
                data=json.dumps(user_data),
                content_type='application/json')
    
    # Try to create second user with same email
    response = client.post('/api/users', 
                          data=json.dumps(user_data),
                          content_type='application/json')
    
    assert response.status_code == 409
    
    data = json.loads(response.data)
    assert 'already exists' in data['error']

def test_create_user_invalid_email(client):
    """Test creating a user with invalid email"""
    user_data = {
        'name': 'John Doe',
        'email': 'invalid-email'
    }
    
    response = client.post('/api/users', 
                          data=json.dumps(user_data),
                          content_type='application/json')
    
    assert response.status_code == 400
    
    data = json.loads(response.data)
    assert 'Validation failed' in data['error']

def test_create_user_empty_name(client):
    """Test creating a user with empty name"""
    user_data = {
        'name': '',
        'email': 'john@example.com'
    }
    
    response = client.post('/api/users', 
                          data=json.dumps(user_data),
                          content_type='application/json')
    
    assert response.status_code == 400

def test_get_users_with_data(client):
    """Test getting users when some exist"""
    # Create a user
    user_data = {
        'name': 'John Doe',
        'email': 'john@example.com'
    }
    
    client.post('/api/users', 
                data=json.dumps(user_data),
                content_type='application/json')
    
    # Get all users
    response = client.get('/api/users')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['name'] == 'John Doe'
    assert data[0]['email'] == 'john@example.com'

def test_web_form_create_user(client):
    """Test creating a user via web form"""
    response = client.post('/user', data={
        'name': 'Jane Doe',
        'email': 'jane@example.com'
    })
    
    assert response.status_code == 302  # Redirect after POST
    
    # Check if user was created
    users_response = client.get('/api/users')
    data = json.loads(users_response.data)
    assert len(data) == 1
    assert data[0]['name'] == 'Jane Doe'
    assert data[0]['email'] == 'jane@example.com'

def test_web_form_validation(client):
    """Test web form validation"""
    response = client.post('/user', data={
        'name': '',
        'email': 'invalid-email'
    })
    
    assert response.status_code == 200  # Returns form with error
    
    # Check that no user was created
    users_response = client.get('/api/users')
    data = json.loads(users_response.data)
    assert len(data) == 0

def test_index_page(client):
    """Test main index page"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'User Management System' in response.data

def test_404_error(client):
    """Test 404 error handling"""
    response = client.get('/nonexistent')
    assert response.status_code == 404
    
    data = json.loads(response.data)
    assert data['error'] == 'Not found'
