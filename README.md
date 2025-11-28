# rule-based-trading
This repository is attempt to build a service that cal run on your local machine and help you execute rule based trades. Currently supports integration with Kite Zerodha.


## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Credentials

```bash
cp .env.example .env
# Edit .env with your Kite Connect credentials
```

```env
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_ACCESS_TOKEN=your_access_token
```

### 3. Define Trading Rules

Edit `rules.yaml`:

```yaml
version: "1.0"

rules:
  - rule_id: "sensex-ce-001"
    name: "SENSEX Call Option"
    trading_symbol: "SENSEX24N2779000CE"
    exchange: "BFO"
    entry_price: 700
    quantity: 10
    position_type: "LONG"
    
    take_profit:
      enabled: true
      condition_type: "relative"
      target: 100              # Exit at 800 (+100)
      order_type: "MARKET"
    
    stop_loss:
      enabled: true
      condition_type: "relative"
      stop: 50                 # Exit at 650 (-50)
      order_type: "MARKET"
```

### 4. Start the Server

```bash
uvicorn main:app --reload
```

### 5. Start the Rule Engine

```bash
curl -X POST http://localhost:8000/engine/start
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

```yaml
stop_loss:
  enabled: true
  condition_type: "relative"
  stop: 50
  trail: true          # Enable trailing
  trail_step: 50       # Maintain 50 points below highest
```

### Time Conditions

```yaml
time_conditions:
  start_time: "09:15"      # Start monitoring
  end_time: "15:15"        # Stop monitoring
  square_off_time: "15:20" # Force exit time
  active_days: [0, 1, 2, 3, 4]  # Mon-Fri
```

## API Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Engine status + rule summary |

### Engine Control

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/engine/start` | POST | Start rule evaluation |
| `/engine/stop` | POST | Stop rule evaluation |

### Rules Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rules` | GET | List all rules |
| `/rules` | POST | Create new rule |
| `/rules/{id}` | GET | Get rule details |
| `/rules/{id}` | PUT | Update rule |
| `/rules/{id}` | DELETE | Delete rule |
| `/rules/{id}/enable` | POST | Enable rule |
| `/rules/{id}/disable` | POST | Disable rule |

### Market Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ltp/{symbol}?exchange=NFO` | GET | Get last traded price |

## Example Usage

### Create a Rule via API

```bash
curl -X POST http://localhost:8000/rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "nifty-pe-001",
    "name": "NIFTY PUT",
    "trading_symbol": "NIFTY24N2724500PE",
    "exchange": "NFO",
    "entry_price": 150,
    "quantity": 50,
    "position_type": "LONG",
    "take_profit": {
      "enabled": true,
      "condition_type": "percentage",
      "target": 50
    },
    "stop_loss": {
      "enabled": true,
      "condition_type": "percentage",
      "stop": 30
    }
  }'
```

### Check Status

```bash
curl http://localhost:8000/status
```

### View Rules

```bash
curl http://localhost:8000/rules
```

## How Rules are Evaluated

1. Engine polls every 1 second (configurable)
2. For each active rule:
   - Fetches current LTP from Kite API
   - Compares against TP/SL thresholds
   - If triggered → places exit order
   - Marks rule as triggered (won't re-trigger)
3. Rules file can be hot-reloaded (edit while running)

## Important Notes

1. **This is an EXIT-only framework** - You place entry orders via Kite UI
2. **One order per rule** - After triggering, rule is marked done
3. **Market hours only** - Respect `time_conditions`
4. **Test thoroughly** - Use paper trading or small quantities first
5. **API limits** - Kite has rate limits, don't poll too aggressively

## Exchanges

- `NSE` - National Stock Exchange (equity)
- `BSE` - Bombay Stock Exchange (equity)
- `NFO` - NSE Futures & Options
- `BFO` - BSE Futures & Options (SENSEX options)
- `MCX` - Multi Commodity Exchange
- `CDS` - Currency Derivatives

## License

MIT
