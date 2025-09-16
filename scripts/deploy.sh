#!/bin/bash

# Decodeat API Deployment Script
set -e

echo "🚀 Starting Decodeat API deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_warning "Please edit .env file with your actual configuration values."
        exit 1
    else
        print_error ".env.example file not found. Cannot create .env file."
        exit 1
    fi
fi

# Check if GCP key file exists
if [ ! -f gcp-key.json ]; then
    print_error "gcp-key.json file not found. Please add your Google Cloud service account key."
    exit 1
fi

# Load environment variables
source .env

# Validate required environment variables
if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your_gemini_api_key_here" ]; then
    print_error "GEMINI_API_KEY is not set in .env file."
    exit 1
fi

print_status "Environment validation passed."

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose down --remove-orphans

# Pull latest images
print_status "Pulling latest images..."
docker-compose pull

# Build application image
print_status "Building application image..."
docker-compose build --no-cache decodeat-api

# Start services
print_status "Starting services..."
docker-compose up -d

# Wait for services to be healthy
print_status "Waiting for services to be healthy..."
sleep 30

# Check service health
print_status "Checking service health..."

# Check ChromaDB
if curl -f http://localhost:8001/api/v1/heartbeat > /dev/null 2>&1; then
    print_status "ChromaDB is healthy ✅"
else
    print_error "ChromaDB health check failed ❌"
fi

# Check FastAPI
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "FastAPI is healthy ✅"
else
    print_error "FastAPI health check failed ❌"
fi

# Show running containers
print_status "Running containers:"
docker-compose ps

print_status "Deployment completed! 🎉"
print_status "API is available at: http://localhost:8000"
print_status "API documentation: http://localhost:8000/docs"
print_status "ChromaDB is available at: http://localhost:8001"

echo ""
print_status "To view logs: docker-compose logs -f"
print_status "To stop services: docker-compose down"
print_status "To restart services: docker-compose restart"