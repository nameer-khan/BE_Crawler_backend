#!/bin/bash

echo "🚀 Starting Web Crawler Development Environment..."

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Remove old volumes (optional - uncomment if you want fresh start)
# echo "🗑️  Removing old volumes..."
# docker-compose down -v

# Build images
echo "🔨 Building Docker images..."
docker-compose build --no-cache

# Start services
echo "▶️  Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service status
echo "📊 Checking service status..."
docker-compose ps

# Show logs
echo "📋 Recent logs:"
docker-compose logs --tail=20

echo "✅ Setup complete! Access the API at: http://localhost:8000/api/"
echo "📚 API Documentation: http://localhost:8000/api/"
echo "🔍 Check logs with: docker-compose logs -f"
