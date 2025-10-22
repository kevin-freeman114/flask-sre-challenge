# AWS Secrets Manager integration
import boto3
import json
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class SecretsManager:
    """AWS Secrets Manager client"""
    
    def __init__(self, region_name='us-east-1'):
        self.client = boto3.client('secretsmanager', region_name=region_name)
    
    def get_secret(self, secret_name):
        """Retrieve a secret from AWS Secrets Manager"""
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except ClientError as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise
    
    def create_secret(self, secret_name, secret_value, description=""):
        """Create a new secret in AWS Secrets Manager"""
        try:
            response = self.client.create_secret(
                Name=secret_name,
                Description=description,
                SecretString=json.dumps(secret_value)
            )
            logger.info(f"Created secret: {secret_name}")
            return response
        except ClientError as e:
            logger.error(f"Failed to create secret {secret_name}: {e}")
            raise
    
    def update_secret(self, secret_name, secret_value):
        """Update an existing secret"""
        try:
            response = self.client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(secret_value)
            )
            logger.info(f"Updated secret: {secret_name}")
            return response
        except ClientError as e:
            logger.error(f"Failed to update secret {secret_name}: {e}")
            raise
    
    def delete_secret(self, secret_name):
        """Delete a secret"""
        try:
            response = self.client.delete_secret(
                SecretId=secret_name,
                ForceDeleteWithoutRecovery=True
            )
            logger.info(f"Deleted secret: {secret_name}")
            return response
        except ClientError as e:
            logger.error(f"Failed to delete secret {secret_name}: {e}")
            raise

# Database configuration using Secrets Manager
def get_database_config():
    """Get database configuration from AWS Secrets Manager"""
    secrets_manager = SecretsManager()
    
    try:
        # Try to get database credentials from Secrets Manager
        db_secret = secrets_manager.get_secret('flask-sre-challenge/database')
        
        return {
            'host': db_secret['host'],
            'port': db_secret['port'],
            'database': db_secret['database'],
            'username': db_secret['username'],
            'password': db_secret['password']
        }
    except Exception as e:
        logger.warning(f"Failed to get database config from Secrets Manager: {e}")
        # Fallback to environment variables
        return {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'port': os.environ.get('DB_PORT', '5432'),
            'database': os.environ.get('DB_NAME', 'flask_app'),
            'username': os.environ.get('DB_USER', 'postgres'),
            'password': os.environ.get('DB_PASSWORD', 'password')
        }

# Application secrets management
def get_app_secrets():
    """Get application secrets from AWS Secrets Manager"""
    secrets_manager = SecretsManager()
    
    try:
        app_secret = secrets_manager.get_secret('flask-sre-challenge/app')
        return app_secret
    except Exception as e:
        logger.warning(f"Failed to get app secrets from Secrets Manager: {e}")
        # Fallback to environment variables
        return {
            'secret_key': os.environ.get('SECRET_KEY', 'dev-secret-key'),
            'encryption_key': os.environ.get('ENCRYPTION_KEY', 'dev-encryption-key')
        }

# Initialize secrets for the application
def initialize_secrets():
    """Initialize application secrets"""
    try:
        secrets_manager = SecretsManager()
        
        # Create database secret if it doesn't exist
        try:
            db_config = {
                'host': os.environ.get('DB_HOST', 'localhost'),
                'port': os.environ.get('DB_PORT', '5432'),
                'database': os.environ.get('DB_NAME', 'flask_app'),
                'username': os.environ.get('DB_USER', 'postgres'),
                'password': os.environ.get('DB_PASSWORD', 'password')
            }
            secrets_manager.create_secret(
                'flask-sre-challenge/database',
                db_config,
                'Database configuration for Flask SRE Challenge'
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceExistsException':
                raise
        
        # Create app secret if it doesn't exist
        try:
            app_secrets = {
                'secret_key': os.environ.get('SECRET_KEY', 'dev-secret-key'),
                'encryption_key': os.environ.get('ENCRYPTION_KEY', 'dev-encryption-key')
            }
            secrets_manager.create_secret(
                'flask-sre-challenge/app',
                app_secrets,
                'Application secrets for Flask SRE Challenge'
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceExistsException':
                raise
        
        logger.info("Secrets initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize secrets: {e}")
        raise

if __name__ == '__main__':
    initialize_secrets()
