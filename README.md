# rule-based-trading

A local service for rule-based automated trading with Kite Connect (Zerodha). Define exit rules with take-profit, stop-loss, and trailing stops - the engine monitors your positions and executes exits automatically.

## Features

- **Multi-user support** - Each user has their own broker credentials and rules
- **Encrypted credentials** - Broker API keys are encrypted in the database
- **Rule-based exits** - Define TP/SL conditions via REST API
- **Trailing stops** - Automatically adjust stop-loss as price moves in your favor
- **Time conditions** - Set trading hours and auto square-off times
- **REST API** - Full control via HTTP endpoints
- **Database storage** - Rules persist in PostgreSQL

## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

```env
SECRET_KEY=your-secret-key-change-this-in-production
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/trading
REDIS_URL=redis://localhost:6379/0
```

### 3. Start the Server

```bash
uvicorn main:app --reload
```

### 4. Create an Account

Register via the API:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure_password"}'
```

### 5. Connect Your Broker

Store your Kite Connect credentials:

```bash
curl -X POST http://localhost:8000/broker/connect \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your_kite_api_key", "api_secret": "your_kite_api_secret"}'
```

### 6. Define Trading Rules

Create rules via the API:

```bash
curl -X POST http://localhost:8000/rules \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SENSEX Call Option",
    "symbol_pattern": "SENSEX*",
    "exchange": "BFO",
    "take_profit": {
      "enabled": true,
      "condition_type": "relative",
      "target": 100
    },
    "stop_loss": {
      "enabled": true,
      "condition_type": "relative",
      "stop": 40
    }
  }'
```

### 7. Start the Rule Engine

```bash
curl -X POST http://localhost:8000/engine/start \
  -H "Authorization: Bearer <your_token>"
```

## Rule Configuration

### Condition Types

| Type | Description | Example |
|------|-------------|---------|
| `relative` | Points from entry | `target: 100` = entry + 100 |
| `percentage` | Percent of entry | `target: 15` = entry × 1.15 |
| `absolute` | Fixed price level | `target: 800` = exit at 800 |

### Position Types

- `LONG`: Bought position → TP triggers on price UP, SL on price DOWN
- `SHORT`: Sold position → TP triggers on price DOWN, SL on price UP

### Trailing Stops

```json
{
  "stop_loss": {
    "enabled": true,
    "condition_type": "relative",
    "stop": 50,
    "trail": true,
    "trail_step": 50
  }
}
```

### Time Conditions

```json
{
  "time_conditions": {
    "start_time": "09:15",
    "end_time": "15:15",
    "square_off_time": "15:20",
    "active_days": [0, 1, 2, 3, 4]
  }
}
```

## API Endpoints

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Create a new account |
| `/auth/login` | POST | Login and get JWT token |
| `/auth/status` | GET | Check authentication status |

### Broker

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/broker/connect` | POST | Store broker credentials |
| `/broker/oauth` | GET | Initiate OAuth flow |
| `/broker/status` | GET | Check broker connection |

### Engine Control

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/engine/start` | POST | Start rule evaluation |
| `/engine/stop` | POST | Stop rule evaluation |
| `/engine/status` | GET | Get engine status |

### Rules Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rules` | GET | List all rules |
| `/rules` | POST | Create new rule |
| `/rules/{id}` | GET | Get rule details |
| `/rules/{id}` | PUT | Update rule |
| `/rules/{id}` | DELETE | Delete rule |

### Positions & Trades

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/positions` | GET | Get current positions |
| `/trades/active` | GET | Get active trades |

## Development

### Run Tests

```bash
pytest tests/ -v
```

### Format Code

```bash
black .
```

### Docker

```bash
docker-compose up -d
```

## License

MIT
