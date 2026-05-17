#!/bin/bash
# Activate virtual environment if present (Azure sets this up automatically in /antenv/env)
source /antenv/env/bin/activate

# Apply database migrations to Azure PostgreSQL
echo "Running database migrations..."
flask db upgrade

# Start Gunicorn targeting the app variable inside app.py
echo "Starting Gunicorn server..."
gunicorn --bind=0.0.0.0 --timeout 600 app:app