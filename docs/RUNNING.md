# Running the Trading System

Complete guide to running the rule-based trading system.

## Architecture

This is a **multi-tenant** system where:
- Users register/login with their own accounts
- Each user provides their **own Kite API credentials**
- No shared `.env` file needed for broker credentials
- System handles multiple users simultaneously

## Prerequisites

- Python 3.10+
- PostgreSQL 14+ (required for multi-user)
- Redis 7+ (for sessions/caching)

## Quick Start

### 1. Start Infrastructure

```bash
# Using Docker (recommended)
docker run -d --name postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=trading -p 5432:5432 postgres:15
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Or using Homebrew (macOS)
brew install postgresql redis
brew services start postgresql
brew services start redis
createdb trading
```

### 2. Configure Server Environment

Create `.env` file (server config only, NO broker credentials):

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/trading

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Authentication (generate a secure key)
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256

# Server
DEBUG=true
LOG_LEVEL=INFO
```

### 3. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Initialize Database

```bash
python -c "
import asyncio
from src.database import get_database, Base

async def init():
    db = get_database()
    await db.connect()
    await db.create_tables()
    print('Database initialized!')

asyncio.run(init())
"
```

### 5. Start the Server

```bash
uvicorn src.api.app:app --reload --port 8000
```

### 6. Verify

```bash
curl http://localhost:8000/health
# {"status": "healthy", "version": "1.0.0"}
```

## User Flow

### 1. Register Account

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trader@example.com",
    "password": "securepass123",
    "name": "Trader"
  }'

# Response:
# {"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer", "expires_in": 1800}
```

### 2. Login (if already registered)

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trader@example.com",
    "password": "securepass123"
  }'
```

### 3. Connect Broker (User provides their OWN API keys)

```bash
export TOKEN="your_access_token_from_login"

curl -X POST http://localhost:8000/auth/broker/connect \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "broker": "kite",
    "api_key": "YOUR_KITE_API_KEY",
    "api_secret": "YOUR_KITE_API_SECRET"
  }'

# Response:
# {"auth_url": "https://kite.zerodha.com/connect/login?...", "state": "abc123"}
```

### 4. Complete OAuth

Open the `auth_url` in your browser to login to Kite and authorize the app.
After authorization, Kite redirects back and the system stores your access token.

### 5. Start Trading

```bash
# Get your positions
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/trading/positions

# Create a trading rule
curl -X POST http://localhost:8000/rules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NIFTY Call Exit",
    "symbol": "NIFTY24D2550000CE",
    "conditions": [{"indicator": "price", "operator": "gte", "value": 250}],
    "actions": [{"action": "sell", "quantity": 50, "order_type": "market"}]
  }'

# Place an order
curl -X POST http://localhost:8000/trading/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "quantity": 10,
    "order_type": "MARKET",
    "position_type": "LONG"
  }'
```

## Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/trading
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  worker:
    build: .
    command: celery -A src.workers.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/trading
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  beat:
    build: .
    command: celery -A src.workers.celery_app beat --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: trading
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

Run with:

```bash
docker-compose up -d
```

## Troubleshooting

### Common Issues

1. **"Import could not be resolved"**
   ```bash
   pip install -r requirements.txt
   ```

2. **Database connection failed**
   ```bash
   # Check PostgreSQL is running
   pg_isready -h localhost -p 5432
   ```

3. **Redis connection failed**
   ```bash
   # Check Redis is running
   redis-cli ping
   ```

4. **Kite authentication expired**
   ```bash
   # Re-authenticate
   curl http://localhost:8000/auth/login
   # Or delete session file
   rm .kite_session.json
   ```

### Logs

```bash
# API logs
tail -f /var/log/trading/api.log

# Worker logs
tail -f /var/log/trading/worker.log

# Or in development, logs appear in terminal
```

## Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/test_engine.py -v
```
