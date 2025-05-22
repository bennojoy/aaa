#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found. Make sure you have created it with:"
    echo "python3.12 -m venv venv"
    echo "source venv/bin/activate"
    echo "pip install -r requirements.txt"
    exit 1
fi

# Check if uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo "❌ uvicorn not found. Installing requirements..."
    pip install -r requirements.txt
fi

# Create logs directory if it doesn't exist
mkdir -p logs

echo "Starting FastAPI server..."
echo "API will be available at:"
echo "- Main API: http://localhost:8000"
echo "- API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "----------------------------------------"

# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 