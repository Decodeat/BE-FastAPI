#!/bin/bash

# Decodeat API Development Script
set -e

echo "🛠️ Starting Decodeat API in development mode..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_status "Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_warning "Please edit .env file with your actual configuration values."
    fi
fi

# Start ChromaDB in Docker (development dependency)
print_status "Starting ChromaDB for development..."
docker-compose up -d chromadb

# Wait for ChromaDB to be ready
print_status "Waiting for ChromaDB to be ready..."
sleep 10

# Check ChromaDB health
if curl -f http://localhost:8001/api/v1/heartbeat > /dev/null 2>&1; then
    print_status "ChromaDB is ready ✅"
else
    print_warning "ChromaDB may not be ready yet. The API will work in vector-generation-only mode."
fi

# Run tests (optional)
if [ "$1" = "--test" ]; then
    print_status "Running tests..."
    python -m pytest tests/ -v
fi

# Start the development server
print_status "Starting development server..."
print_status "API will be available at: http://localhost:8000"
print_status "API documentation: http://localhost:8000/docs"
print_status "Press Ctrl+C to stop the server"

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload