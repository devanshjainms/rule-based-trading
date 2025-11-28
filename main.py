"""
KiteAPI Rule-Based Trading Server.

Auto-detects positions from Kite account, matches them to exit rules,
and triggers TP/SL orders using real-time price data.

:copyright: (c) 2025
:license: MIT
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.client import KiteClient
from src.ticker import KiteTickerClient
from src.config import get_config
from src.rules import (
    RulesParser,
    TradingEngine,
    ExitRule,
    TakeProfitCondition,
    StopLossCondition,
    TimeCondition,
    ActiveTrade,
)
from src.exceptions import KiteException


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


kite_client: Optional[KiteClient] = None
ticker_client: Optional[KiteTickerClient] = None
rules_parser: Optional[RulesParser] = None
trading_engine: Optional[TradingEngine] = None


class RuleRequest(BaseModel):
    """
    Request model for creating/updating a rule.

    :ivar rule_id: Unique identifier for the rule.
    :ivar name: Human-readable name for the rule.
    :ivar symbol_pattern: Regex pattern to match symbols.
    :ivar exchange: Exchange filter (optional).
    :ivar apply_to: Position type filter ("ALL", "LONG", "SHORT").
    :ivar take_profit: Take profit configuration.
    :ivar stop_loss: Stop loss configuration.
    :ivar time_conditions: Time-based exit conditions.
    :ivar tags: Tags for categorization.
    :ivar notes: Additional notes.
    """

    rule_id: str
    name: str
    symbol_pattern: str
    exchange: Optional[str] = None
    apply_to: str = "ALL"
    take_profit: Optional[Dict[str, Any]] = None
    stop_loss: Optional[Dict[str, Any]] = None
    time_conditions: Optional[Dict[str, Any]] = None
    tags: List[str] = []
    notes: Optional[str] = None


async def on_exit_trigger(trade: ActiveTrade, trigger_type: str) -> None:
    """
    Handle exit trigger by placing sell order.

    :param trade: The triggered trade containing position and rule.
    :type trade: ActiveTrade
    :param trigger_type: Type of exit ("TP", "SL", or "SQUARE_OFF").
    :type trigger_type: str
    :returns: None
    :rtype: None
    """
    pos = trade.position
    rule = trade.rule

    logger.info(
        f"EXIT: {pos.trading_symbol} {trigger_type} "
        f"@ {trade.current_price:.2f} (entry: {pos.entry_price:.2f})"
    )

    if kite_client is None:
        logger.error("Cannot place order: client not initialized")
        return

    transaction_type = "SELL" if pos.position_type == "LONG" else "BUY"

    if trigger_type == "TP" and rule.take_profit:
        order_type = rule.take_profit.order_type.value
    elif trigger_type == "SL" and rule.stop_loss:
        order_type = rule.stop_loss.order_type.value
    else:
        order_type = "MARKET"

    try:
        order_id = kite_client.place_order(
            variety="regular",
            exchange=pos.exchange,
            tradingsymbol=pos.trading_symbol,
            transaction_type=transaction_type,
            quantity=pos.abs_quantity,
            product=pos.product,
            order_type=order_type,
            tag=f"{trigger_type}_{rule.rule_id[:8]}",
        )
        logger.info(f"Order placed: {order_id}")
    except KiteException as e:
        logger.error(f"Order failed: {e}")
    except Exception as e:
        logger.error(f"Order error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    App lifespan context manager - initialize and cleanup.

    Initializes Kite client, ticker client, rules parser, and trading engine
    on startup. Cleans up by stopping trading engine on shutdown.

    :param app: The FastAPI application instance.
    :type app: FastAPI
    :yields: None
    """
    global kite_client, ticker_client, rules_parser, trading_engine

    config = get_config()

    if config.is_configured():
        kite_client = KiteClient()
        logger.info("Kite client initialized")

        if config.access_token:
            try:
                ticker_client = KiteTickerClient()
                logger.info("Ticker client initialized")
            except Exception as e:
                logger.warning(f"Ticker init failed (will use LTP polling): {e}")
    else:
        logger.warning("Kite credentials not configured")
        logger.warning("Set KITE_API_KEY and KITE_ACCESS_TOKEN in .env")

    rules_parser = RulesParser("rules.yaml")
    logger.info("Rules parser initialized")

    if kite_client:
        trading_engine = TradingEngine(
            kite_client=kite_client,
            ticker_client=ticker_client,
            rules_parser=rules_parser,
            on_trigger=on_exit_trigger,
            position_poll_interval=2.0,
            price_poll_interval=1.0,
        )
        logger.info("Trading engine initialized")

    yield

    if trading_engine and trading_engine.is_running():
        await trading_engine.stop()


app = FastAPI(
    title="KiteAPI Trading Engine",
    description="Auto-detect positions, apply exit rules, trigger TP/SL orders",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health():
    """
    Health check endpoint.

    :returns: Health status with connection information.
    :rtype: dict
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "kite_connected": kite_client is not None,
        "engine_running": trading_engine.is_running() if trading_engine else False,
    }


@app.get("/status", tags=["Health"])
async def status():
    """
    Get engine status.

    :returns: Current engine status and statistics.
    :rtype: dict
    """
    if trading_engine is None:
        return {"running": False, "message": "Engine not initialized"}

    return trading_engine.get_status()


@app.post("/engine/start", tags=["Engine"])
async def start_engine():
    """
    Start the trading engine.

    :returns: Start confirmation and status.
    :rtype: dict
    :raises HTTPException: 503 if engine not initialized.
    """
    if trading_engine is None:
        raise HTTPException(503, "Engine not initialized (check credentials)")

    if trading_engine.is_running():
        return {"message": "Already running"}

    await trading_engine.start()
    return {"message": "Engine started", "status": trading_engine.get_status()}


@app.post("/engine/stop", tags=["Engine"])
async def stop_engine():
    """
    Stop the trading engine.

    :returns: Stop confirmation.
    :rtype: dict
    :raises HTTPException: 503 if engine not initialized.
    """
    if trading_engine is None:
        raise HTTPException(503, "Engine not initialized")

    if not trading_engine.is_running():
        return {"message": "Not running"}

    await trading_engine.stop()
    return {"message": "Engine stopped"}


@app.get("/positions", tags=["Positions"])
async def get_positions():
    """
    Get current positions from account.

    :returns: List of open positions with details.
    :rtype: dict
    :raises HTTPException: 503 if client not initialized, 500 on error.
    """
    if kite_client is None:
        raise HTTPException(503, "Client not initialized")

    try:
        positions = kite_client.positions()
        net = positions.get("net", [])
        return {
            "total": len([p for p in net if p.get("quantity", 0) != 0]),
            "positions": [
                {
                    "symbol": p["tradingsymbol"],
                    "exchange": p["exchange"],
                    "quantity": p["quantity"],
                    "average_price": p["average_price"],
                    "last_price": p["last_price"],
                    "pnl": p["pnl"],
                    "product": p["product"],
                }
                for p in net
                if p.get("quantity", 0) != 0
            ],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/trades/active", tags=["Positions"])
async def get_active_trades():
    """
    Get trades being monitored by engine.

    :returns: List of active trades with monitoring details.
    :rtype: dict
    :raises HTTPException: 503 if engine not initialized.
    """
    if trading_engine is None:
        raise HTTPException(503, "Engine not initialized")

    return {"trades": trading_engine.get_active_trades()}


@app.get("/rules", tags=["Rules"])
async def list_rules():
    """
    List all exit rules.

    :returns: All configured rules with details.
    :rtype: dict
    :raises HTTPException: 503 if parser not initialized, 500 on error.
    """
    if rules_parser is None:
        raise HTTPException(503, "Parser not initialized")

    try:
        config = rules_parser.load()
        return {
            "version": config.version,
            "total": len(config.rules),
            "defaults_enabled": config.defaults.enabled if config.defaults else False,
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "enabled": r.enabled,
                    "symbol_pattern": r.symbol_pattern,
                    "exchange": r.exchange,
                    "apply_to": r.apply_to,
                    "take_profit": (
                        r.take_profit.model_dump() if r.take_profit else None
                    ),
                    "stop_loss": r.stop_loss.model_dump() if r.stop_loss else None,
                    "tags": r.tags,
                }
                for r in config.rules
            ],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/rules/{rule_id}", tags=["Rules"])
async def get_rule(rule_id: str):
    """
    Get a specific rule by ID.

    :param rule_id: The unique rule identifier.
    :type rule_id: str
    :returns: Rule details.
    :rtype: dict
    :raises HTTPException: 404 if rule not found, 503 if parser not initialized.
    """
    if rules_parser is None:
        raise HTTPException(503, "Parser not initialized")

    config = rules_parser.load()
    rule = config.get_rule(rule_id)

    if rule is None:
        raise HTTPException(404, f"Rule '{rule_id}' not found")

    return {
        "rule_id": rule.rule_id,
        "name": rule.name,
        "enabled": rule.enabled,
        "symbol_pattern": rule.symbol_pattern,
        "exchange": rule.exchange,
        "apply_to": rule.apply_to,
        "take_profit": rule.take_profit.model_dump() if rule.take_profit else None,
        "stop_loss": rule.stop_loss.model_dump() if rule.stop_loss else None,
        "time_conditions": (
            rule.time_conditions.model_dump() if rule.time_conditions else None
        ),
        "tags": rule.tags,
        "notes": rule.notes,
    }


@app.post("/rules", tags=["Rules"])
async def create_rule(req: RuleRequest):
    """
    Create a new exit rule.

    :param req: Rule configuration request.
    :type req: RuleRequest
    :returns: Creation confirmation with rule ID.
    :rtype: dict
    :raises HTTPException: 400 if rule invalid, 503 if parser not initialized.
    """
    if rules_parser is None:
        raise HTTPException(503, "Parser not initialized")

    rule = ExitRule(
        rule_id=req.rule_id,
        name=req.name,
        symbol_pattern=req.symbol_pattern,
        exchange=req.exchange,
        apply_to=req.apply_to,
        take_profit=TakeProfitCondition(**req.take_profit) if req.take_profit else None,
        stop_loss=StopLossCondition(**req.stop_loss) if req.stop_loss else None,
        time_conditions=(
            TimeCondition(**req.time_conditions) if req.time_conditions else None
        ),
        tags=req.tags,
        notes=req.notes,
    )

    try:
        rules_parser.add_rule(rule)
        return {"message": "Rule created", "rule_id": rule.rule_id}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/rules/{rule_id}", tags=["Rules"])
async def delete_rule(rule_id: str):
    """
    Delete a rule by ID.

    :param rule_id: The unique rule identifier.
    :type rule_id: str
    :returns: Deletion confirmation.
    :rtype: dict
    :raises HTTPException: 404 if rule not found, 503 if parser not initialized.
    """
    if rules_parser is None:
        raise HTTPException(503, "Parser not initialized")

    try:
        rules_parser.delete_rule(rule_id)
        return {"message": "Rule deleted", "rule_id": rule_id}
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/rules/{rule_id}/enable", tags=["Rules"])
async def enable_rule(rule_id: str):
    """
    Enable a rule by ID.

    :param rule_id: The unique rule identifier.
    :type rule_id: str
    :returns: Enable confirmation.
    :rtype: dict
    :raises HTTPException: 404 if rule not found, 503 if parser not initialized.
    """
    if rules_parser is None:
        raise HTTPException(503, "Parser not initialized")

    try:
        rules_parser.update_rule(rule_id, {"enabled": True})
        return {"message": "Rule enabled"}
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/rules/{rule_id}/disable", tags=["Rules"])
async def disable_rule(rule_id: str):
    """
    Disable a rule by ID.

    :param rule_id: The unique rule identifier.
    :type rule_id: str
    :returns: Disable confirmation.
    :rtype: dict
    :raises HTTPException: 404 if rule not found, 503 if parser not initialized.
    """
    if rules_parser is None:
        raise HTTPException(503, "Parser not initialized")

    try:
        rules_parser.update_rule(rule_id, {"enabled": False})
        return {"message": "Rule disabled"}
    except ValueError as e:
        raise HTTPException(404, str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
