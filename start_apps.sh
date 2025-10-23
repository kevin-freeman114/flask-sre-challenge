#!/bin/bash

echo "Starting Flask SRE Challenge Applications..."
echo "Main App: http://0.0.0.0:5000"
echo "Monitoring App: http://0.0.0.0:5001"

# Fix database schema first
echo "Fixing database schema..."
python fix_database.py

# Start main app in background
python main_app.py &
MAIN_PID=$!

# Start monitoring app in background  
python monitoring_app.py &
MONITORING_PID=$!

# Function to handle shutdown
cleanup() {
    echo "Shutting down applications..."
    kill $MAIN_PID $MONITORING_PID
    wait
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Wait for both processes
wait
