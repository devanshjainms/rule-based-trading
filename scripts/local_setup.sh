#!/bin/bash
# Local Development Setup Script
# Run this to start PostgreSQL, Redis, and the API server

set -e

echo "🚀 Rule-Based Trading - Local Setup"
echo "===================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker Desktop.${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker is not running. Please start Docker Desktop.${NC}"
    echo "   On macOS: Open Docker Desktop from Applications"
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# Start PostgreSQL and Redis
echo ""
echo "📦 Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check PostgreSQL
until docker exec trading-postgres pg_isready -U postgres &> /dev/null; do
    echo "   Waiting for PostgreSQL..."
    sleep 2
done
echo -e "${GREEN}✓ PostgreSQL is ready${NC}"

# Check Redis
until docker exec trading-redis redis-cli ping &> /dev/null; do
    echo "   Waiting for Redis..."
    sleep 2
done
echo -e "${GREEN}✓ Redis is ready${NC}"

# Activate virtual environment
echo ""
echo "🐍 Setting up Python environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Initialize database
echo ""
echo "🗄️  Initializing database..."
python3 << 'EOF'
import asyncio
import sys

async def init_db():
    try:
        from src.database.connection import get_database
        
        db = get_database()
        await db.connect()
        await db.create_tables()
        print("✓ Database tables created")
        await db.disconnect()
    except Exception as e:
        print(f"⚠️  Database init warning: {e}")
        print("   (This is OK if tables already exist)")

asyncio.run(init_db())
EOF

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "===================================="
echo "To start the API server, run:"
echo ""
echo "  source .venv/bin/activate"
echo "  uvicorn src.api.app:app --reload --port 8000"
echo ""
echo "Then test with:"
echo ""
echo "  curl http://localhost:8000/health"
echo ""
echo "===================================="
