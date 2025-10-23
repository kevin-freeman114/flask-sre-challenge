#!/usr/bin/env python3
"""
Startup script to run both main app and monitoring app
"""
import os
import sys
import subprocess
import time
import signal
import threading
from multiprocessing import Process

def run_main_app():
    """Run the main application on port 5000"""
    os.environ['PORT'] = '5000'
    os.environ['FLASK_ENV'] = 'production'
    
    try:
        from main_app import app, init_db
        init_db()
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"Error starting main app: {e}")
        sys.exit(1)

def run_monitoring_app():
    """Run the monitoring application on port 5001"""
    os.environ['MONITORING_PORT'] = '5001'
    os.environ['FLASK_ENV'] = 'production'
    
    try:
        from monitoring_app import app, init_db
        init_db()
        app.run(host='0.0.0.0', port=5001, debug=False)
    except Exception as e:
        print(f"Error starting monitoring app: {e}")
        sys.exit(1)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("Received shutdown signal, stopping applications...")
    sys.exit(0)

if __name__ == '__main__':
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Starting Flask SRE Challenge Applications...")
    print("Main App: http://0.0.0.0:5000")
    print("Monitoring App: http://0.0.0.0:5001")
    
    # Start main app in a separate process
    main_process = Process(target=run_main_app)
    main_process.start()
    
    # Start monitoring app in a separate process
    monitoring_process = Process(target=run_monitoring_app)
    monitoring_process.start()
    
    try:
        # Wait for both processes
        main_process.join()
        monitoring_process.join()
    except KeyboardInterrupt:
        print("Shutting down applications...")
        main_process.terminate()
        monitoring_process.terminate()
        main_process.join()
        monitoring_process.join()
