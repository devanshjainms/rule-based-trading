"""
Trading Engine - Matches positions to rules, uses ticker for prices.

This module provides the main trading engine that orchestrates:

1. Monitoring positions from account (via PositionMonitor)
2. Matching positions to exit rules from database
3. Subscribing to ticker for real-time prices
4. Evaluating TP/SL conditions
5. Placing exit orders when triggered

:copyright: (c) 2025
:license: MIT
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from dataclasses import dataclass

from .schema import (
    ConditionType,
    ExitRule,
    StopLossCondition,
    TakeProfitCondition,
    TimeCondition,
    TradingConfig,
)
from ..core.repositories import RulesRepository
from ..monitor import PositionMonitor, TrackedPosition

logger = logging.getLogger(__name__)


@dataclass
class ActiveTrade:
    """
    An active trade being monitored for exit conditions.

    Combines position data with matched rule and tracks price movements.

    :ivar position: The tracked position from the account.
    :ivar rule: The exit rule matched to this position.
    :ivar tp_price: Calculated take-profit trigger price.
    :ivar sl_price: Calculated stop-loss trigger price.
    :ivar current_price: Current market price.
    :ivar highest_price: Highest price since tracking started.
    :ivar lowest_price: Lowest price since tracking started.
    :ivar triggered: Whether exit has been triggered.
    :ivar trigger_type: Type of trigger (TP, SL, SQUARE_OFF).
    :ivar triggered_at: Timestamp when triggered.
    """

    position: TrackedPosition
    rule: ExitRule
    tp_price: Optional[float]
    sl_price: Optional[float]
    current_price: float = 0.0
    highest_price: float = 0.0
    lowest_price: float = 0.0
    triggered: bool = False
    trigger_type: Optional[str] = None
    triggered_at: Optional[datetime] = None

    @property
    def symbol_key(self) -> str:
        """
        Get the unique symbol key for this trade.

        :returns: Symbol key in format "EXCHANGE:SYMBOL".
        :rtype: str
        """
        return self.position.symbol_key

    def update_price(self, price: float) -> None:
        """
        Update current price and track high/low watermarks.

        :param price: The new current price.
        :type price: float
        """
        self.current_price = price
        if price > self.highest_price:
            self.highest_price = price
        if self.lowest_price == 0 or price < self.lowest_price:
            self.lowest_price = price


class TradingEngine:
    """
    Main trading engine for automated exit management.

    Orchestrates position monitoring, price streaming, and rule evaluation.
    Supports both WebSocket ticker for real-time prices and LTP polling
    as a fallback.

    :param kite_client: Initialized KiteClient instance.
    :type kite_client: Any
    :param rules_repository: RulesRepository instance for loading rules from database.
    :type rules_repository: RulesRepository
    :param user_id: User ID whose rules to load.
    :type user_id: str
    :param ticker_client: Optional KiteTickerClient for real-time prices.
    :type ticker_client: Any
    :param on_trigger: Callback function when exit triggers.
    :type on_trigger: Optional[Callable]
    :param position_poll_interval: Seconds between position polls.
    :type position_poll_interval: float
    :param price_poll_interval: Seconds between price polls (fallback mode).
    :type price_poll_interval: float

    :ivar position_monitor: PositionMonitor instance.
    :ivar _running: Whether engine is currently running.
    :ivar _active_trades: Dictionary of active trades being monitored.
    :ivar _prices: Cache of instrument token to price mappings.
    :ivar _config: Current trading configuration.

    Example::

        engine = TradingEngine(
            kite_client=client,
            rules_repository=rules_repo,
            user_id="user-123",
            on_trigger=handle_exit,
        )
        await engine.start()

        status = engine.get_status()

        await engine.stop()
    """

    def __init__(
        self,
        kite_client: Any,
        rules_repository: RulesRepository,
        user_id: str,
        ticker_client: Any = None,
        on_trigger: Optional[Callable] = None,
        position_poll_interval: float = 1.0,
        price_poll_interval: float = 1.0,
        rules_refresh_interval: float = 1.0,
    ) -> None:
        """
        Initialize the trading engine.

        :param kite_client: Initialized KiteClient instance.
        :type kite_client: Any
        :param rules_repository: RulesRepository instance for loading rules.
        :type rules_repository: RulesRepository
        :param user_id: User ID whose rules to load.
        :type user_id: str
        :param ticker_client: Optional KiteTickerClient for real-time prices.
        :type ticker_client: Any
        :param on_trigger: Callback function when exit triggers.
        :type on_trigger: Optional[Callable]
        :param position_poll_interval: Seconds between position polls.
        :type position_poll_interval: float
        :param price_poll_interval: Seconds between price polls (fallback mode).
        :type price_poll_interval: float
        :param rules_refresh_interval: Seconds between rules refresh from database.
        :type rules_refresh_interval: float
        """
        self.kite_client = kite_client
        self.ticker_client = ticker_client
        self.rules_repository = rules_repository
        self.user_id = user_id
        self.on_trigger = on_trigger
        self.position_poll_interval = position_poll_interval
        self.price_poll_interval = price_poll_interval
        self.rules_refresh_interval = rules_refresh_interval

        self.position_monitor: Optional[PositionMonitor] = None
        self._running = False
        self._price_task: Optional[asyncio.Task] = None
        self._rules_task: Optional[asyncio.Task] = None
        self._ticker_connected = False
        self._active_trades: Dict[str, ActiveTrade] = {}
        self._triggered_symbols: Set[str] = set()
        self._prices: Dict[int, float] = {}
        self._config: Optional[TradingConfig] = None
        self._rules: List[ExitRule] = []
        self._rules_loaded = False

    def _db_rule_to_exit_rule(self, db_rule: Dict[str, Any]) -> ExitRule:
        """
        Convert a database rule dict to an ExitRule schema object.

        :param db_rule: Rule dictionary from database.
        :type db_rule: Dict[str, Any]
        :returns: ExitRule schema object.
        :rtype: ExitRule
        """
        tp_data = db_rule.get("take_profit", {})
        sl_data = db_rule.get("stop_loss", {})
        tc_data = db_rule.get("time_conditions", {})

        take_profit = None
        if tp_data and tp_data.get("enabled", True):
            take_profit = TakeProfitCondition(
                enabled=tp_data.get("enabled", True),
                condition_type=ConditionType(
                    tp_data.get("condition_type", "relative")
                ),
                target=tp_data.get("target", 0),
                trail=tp_data.get("trail", False),
                trail_step=tp_data.get("trail_step"),
            )

        stop_loss = None
        if sl_data and sl_data.get("enabled", True):
            stop_loss = StopLossCondition(
                enabled=sl_data.get("enabled", True),
                condition_type=ConditionType(
                    sl_data.get("condition_type", "relative")
                ),
                stop=sl_data.get("stop", 0),
                trail=sl_data.get("trail", False),
                trail_step=sl_data.get("trail_step"),
            )

        time_conditions = None
        if tc_data:
            time_conditions = TimeCondition(
                start_time=tc_data.get("start_time"),
                end_time=tc_data.get("end_time"),
                square_off_time=tc_data.get("square_off_time"),
                active_days=tc_data.get("active_days", [0, 1, 2, 3, 4]),
            )

        return ExitRule(
            rule_id=db_rule.get("id", ""),
            name=db_rule.get("name", ""),
            symbol_pattern=db_rule.get("symbol_pattern") or "*",
            exchange=db_rule.get("exchange"),
            apply_to=db_rule.get("position_type") or "ALL",
            take_profit=take_profit,
            stop_loss=stop_loss,
            time_conditions=time_conditions,
        )

    def _find_matching_rule(
        self, symbol: str, exchange: str, position_type: str
    ) -> Optional[ExitRule]:
        """
        Find a matching rule for a position.

        :param symbol: Trading symbol.
        :type symbol: str
        :param exchange: Exchange.
        :type exchange: str
        :param position_type: Position type (LONG/SHORT).
        :type position_type: str
        :returns: Matching rule or None.
        :rtype: Optional[ExitRule]
        """
        for rule in self._rules:
            if rule.exchange and rule.exchange != exchange:
                continue
            if rule.apply_to != "ALL" and rule.apply_to != position_type:
                continue
            if rule.symbol_pattern:
                pattern = rule.symbol_pattern.replace("*", ".*")
                if not re.match(f"^{pattern}$", symbol, re.IGNORECASE):
                    continue
            return rule
        return None

    def _on_new_position(self, position: TrackedPosition) -> None:
        """
        Handle new position detected by the monitor.

        Matches the position to a rule and starts tracking it.

        :param position: The newly detected position.
        :type position: TrackedPosition
        """
        if position.quantity == 0:
            return

        rule = self._find_matching_rule(
            position.trading_symbol, position.exchange, position.position_type
        )

        if rule is None:
            logger.info(f"No rule for {position.trading_symbol}, skipping")
            return

        tp_price = rule.calc_tp(position.entry_price, position.position_type)
        sl_price = rule.calc_sl(position.entry_price, position.position_type)
        trade = ActiveTrade(
            position=position,
            rule=rule,
            tp_price=tp_price,
            sl_price=sl_price,
            current_price=position.last_price,
            highest_price=position.last_price,
            lowest_price=position.last_price,
        )

        self._active_trades[position.symbol_key] = trade

        logger.info(
            f"Tracking: {position.trading_symbol} {position.position_type} "
            f"entry={position.entry_price:.2f} TP={tp_price} SL={sl_price}"
        )
        if self.ticker_client and position.instrument_token:
            try:
                self.ticker_client.subscribe([position.instrument_token])
                self.ticker_client.set_mode(
                    self.ticker_client.MODE_LTP, [position.instrument_token]
                )
            except Exception as e:
                logger.warning(f"Ticker subscribe failed: {e}")

    def _on_position_closed(self, position: TrackedPosition) -> None:
        """
        Handle position closed event.

        Removes the position from active tracking.

        :param position: The closed position.
        :type position: TrackedPosition
        """
        key = position.symbol_key
        if key in self._active_trades:
            del self._active_trades[key]
            logger.info(f"Stopped tracking closed position: {position.trading_symbol}")

    def _on_ticks(self, ws: Any, ticks: List[Dict]) -> None:
        """
        Handle incoming ticker data.

        Updates the price cache with latest tick data.

        :param ws: WebSocket instance.
        :type ws: Any
        :param ticks: List of tick data dictionaries.
        :type ticks: List[Dict]
        """
        for tick in ticks:
            token = tick.get("instrument_token")
            price = tick.get("last_price")
            if token and price:
                self._prices[token] = price

    def _is_within_time(self, tc: Optional[TimeCondition]) -> bool:
        """
        Check if current time is within the trading time window.

        :param tc: Time condition to check, or None to use defaults.
        :type tc: Optional[TimeCondition]
        :returns: True if within trading hours, False otherwise.
        :rtype: bool
        """
        if tc is None:
            tc = self._config.default_time_conditions if self._config else None
        if tc is None:
            return True

        now = datetime.now()
        if now.weekday() not in tc.active_days:
            return False
        current = now.strftime("%H:%M")
        if tc.start_time and current < tc.start_time:
            return False
        if tc.end_time and current > tc.end_time:
            return False

        return True

    def _should_square_off(self, tc: Optional[TimeCondition]) -> bool:
        """
        Check if positions should be force squared off.

        :param tc: Time condition to check, or None to use defaults.
        :type tc: Optional[TimeCondition]
        :returns: True if square-off time has passed, False otherwise.
        :rtype: bool
        """
        if tc is None:
            tc = self._config.default_time_conditions if self._config else None
        if tc is None or tc.square_off_time is None:
            return False

        current = datetime.now().strftime("%H:%M")
        return current >= tc.square_off_time

    async def _evaluate_trade(self, trade: ActiveTrade) -> Optional[str]:
        """
        Evaluate a trade for exit conditions.

        Checks TP, SL, trailing conditions, and time-based square-off.

        :param trade: The trade to evaluate.
        :type trade: ActiveTrade
        :returns: Trigger type (TP, SL, SQUARE_OFF) or None if no trigger.
        :rtype: Optional[str]
        """
        if trade.triggered:
            return None
        token = trade.position.instrument_token
        price = self._prices.get(token, trade.current_price)
        trade.update_price(price)

        rule = trade.rule
        pos = trade.position
        if not self._is_within_time(rule.time_conditions):
            return None
        if self._should_square_off(rule.time_conditions):
            return "SQUARE_OFF"
        if rule.take_profit and rule.take_profit.trail and rule.take_profit.enabled:
            trail_step = rule.take_profit.trail_step or 0
            if trade.tp_price and pos.position_type == "LONG":
                if trade.highest_price >= trade.tp_price:
                    trail_trigger = trade.highest_price - trail_step
                    if price <= trail_trigger:
                        return "TP"
            elif trade.tp_price and pos.position_type == "SHORT":
                if trade.lowest_price <= trade.tp_price:
                    trail_trigger = trade.lowest_price + trail_step
                    if price >= trail_trigger:
                        return "TP"
        elif rule.check_tp(price, pos.entry_price, pos.position_type):
            return "TP"
        if rule.stop_loss and rule.stop_loss.trail and rule.stop_loss.enabled:
            if pos.position_type == "LONG":
                trail_sl = trade.highest_price - rule.stop_loss.stop
                if price <= trail_sl:
                    return "SL"
            else:
                trail_sl = trade.lowest_price + rule.stop_loss.stop
                if price >= trail_sl:
                    return "SL"
        elif rule.check_sl(price, pos.entry_price, pos.position_type):
            return "SL"

        return None

    async def _trigger_exit(self, trade: ActiveTrade, trigger_type: str) -> None:
        """
        Execute an exit trigger.

        Marks the trade as triggered and calls the on_trigger callback.

        :param trade: The trade that triggered.
        :type trade: ActiveTrade
        :param trigger_type: Type of trigger (TP, SL, SQUARE_OFF).
        :type trigger_type: str
        """
        trade.triggered = True
        trade.trigger_type = trigger_type
        trade.triggered_at = datetime.now()

        pos = trade.position

        logger.info(
            f"EXIT TRIGGERED: {pos.trading_symbol} {trigger_type} "
            f"price={trade.current_price:.2f} entry={pos.entry_price:.2f}"
        )

        if self.on_trigger:
            try:
                if asyncio.iscoroutinefunction(self.on_trigger):
                    await self.on_trigger(trade, trigger_type)
                else:
                    self.on_trigger(trade, trigger_type)
            except Exception as e:
                logger.error(f"Trigger callback error: {e}")

    async def _price_loop(self) -> None:
        """
        Fallback price polling loop when WebSocket ticker is unavailable.

        Polls LTP via REST API and evaluates trades for exit conditions.
        """
        while self._running:
            try:
                tokens = [
                    t.position.instrument_token for t in self._active_trades.values()
                ]

                if tokens:
                    symbols = [
                        f"{t.position.exchange}:{t.position.trading_symbol}"
                        for t in self._active_trades.values()
                    ]

                    try:
                        ltp_data = self.kite_client.ltp(*symbols)
                        for sym, data in ltp_data.items():
                            for trade in self._active_trades.values():
                                if trade.symbol_key == sym:
                                    self._prices[trade.position.instrument_token] = (
                                        data["last_price"]
                                    )
                                    break
                    except Exception as e:
                        logger.error(f"LTP fetch error: {e}")
                for trade in list(self._active_trades.values()):
                    trigger = await self._evaluate_trade(trade)
                    if trigger:
                        await self._trigger_exit(trade, trigger)

            except Exception as e:
                logger.error(f"Price loop error: {e}")

            await asyncio.sleep(self.price_poll_interval)

    async def _load_rules(self) -> None:
        """
        Load rules from the database for the user.

        Fetches rules from the rules repository and converts them to ExitRule objects.
        """
        rules_data = await self.rules_repository.get_rules(self.user_id)
        self._rules = []

        if rules_data:
            for rule_dict in rules_data.get("rules", []):
                if rule_dict.get("is_active", True):
                    exit_rule = self._db_rule_to_exit_rule(rule_dict)
                    self._rules.append(exit_rule)

        self._rules_loaded = True
        logger.info(f"Loaded {len(self._rules)} rules for user {self.user_id}")

    async def reload_rules(self) -> None:
        """
        Reload rules from the database.

        Can be called to refresh rules without restarting the engine.
        """
        await self._load_rules()

    async def _rules_refresh_loop(self) -> None:
        """
        Background loop to periodically refresh rules from database.

        Runs every rules_refresh_interval seconds to keep rules up-to-date.
        """
        while self._running:
            try:
                await asyncio.sleep(self.rules_refresh_interval)
                if self._running:
                    await self._load_rules()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Rules refresh error: {e}")

    async def start(self) -> None:
        """
        Start the trading engine.

        Initializes the position monitor, connects to ticker (if available),
        and begins monitoring for exit conditions.

        Example::

            await engine.start()
        """
        if self._running:
            return

        self._running = True
        await self._load_rules()
        self.position_monitor = PositionMonitor(
            kite_client=self.kite_client,
            poll_interval=self.position_poll_interval,
            on_new_position=self._on_new_position,
            on_position_closed=self._on_position_closed,
        )
        await self.position_monitor.start()
        if self.ticker_client:
            try:
                self.ticker_client.on_ticks = self._on_ticks
                self.ticker_client.connect(threaded=True)
                self._ticker_connected = True
                logger.info("Ticker connected")
            except Exception as e:
                logger.warning(f"Ticker failed, using LTP polling: {e}")
                self._price_task = asyncio.create_task(self._price_loop())
        else:
            logger.info("No ticker, using LTP polling")
            self._price_task = asyncio.create_task(self._price_loop())

        self._rules_task = asyncio.create_task(self._rules_refresh_loop())
        logger.info(
            f"Trading engine started (rules refresh every {self.rules_refresh_interval}s)"
        )

    async def stop(self) -> None:
        """
        Stop the trading engine.

        Stops position monitoring, disconnects ticker, and cancels price polling.

        Example::

            await engine.stop()
        """
        self._running = False

        if self.position_monitor:
            await self.position_monitor.stop()

        if self._rules_task:
            self._rules_task.cancel()
            try:
                await self._rules_task
            except asyncio.CancelledError:
                pass

        if self._price_task:
            self._price_task.cancel()
            try:
                await self._price_task
            except asyncio.CancelledError:
                pass

        if self.ticker_client and self._ticker_connected:
            try:
                self.ticker_client.close()
            except:
                pass

        logger.info("Trading engine stopped")

    def is_running(self) -> bool:
        """
        Check if the engine is currently running.

        :returns: True if running, False otherwise.
        :rtype: bool
        """
        return self._running

    def get_active_trades(self) -> List[Dict]:
        """
        Get all active trades being monitored.

        :returns: List of trade dictionaries with position and rule details.
        :rtype: List[Dict]

        Example::

            trades = engine.get_active_trades()
            for trade in trades:
                print(f"{trade['symbol']}: P&L = {trade['pnl']}")
        """
        return [
            {
                "symbol": t.position.trading_symbol,
                "exchange": t.position.exchange,
                "position_type": t.position.position_type,
                "quantity": t.position.quantity,
                "entry_price": t.position.entry_price,
                "current_price": t.current_price,
                "tp_price": t.tp_price,
                "sl_price": t.sl_price,
                "pnl": (t.current_price - t.position.entry_price) * t.position.quantity,
                "rule_id": t.rule.rule_id,
                "triggered": t.triggered,
            }
            for t in self._active_trades.values()
        ]

    def get_status(self) -> Dict:
        """
        Get the current engine status.

        :returns: Dictionary with engine status information.
        :rtype: Dict

        Example::

            status = engine.get_status()
            print(f"Running: {status['running']}")
            print(f"Active trades: {status['active_trades']}")
        """
        return {
            "running": self._running,
            "ticker_connected": self._ticker_connected,
            "active_trades": len(self._active_trades),
            "positions_monitored": (
                len(self.position_monitor.get_positions())
                if self.position_monitor
                else 0
            ),
            "rules_loaded": len(self._rules),
        }
