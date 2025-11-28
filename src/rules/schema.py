"""
Trading Rules Schema - Exit Conditions Only.

This module defines the Pydantic models for trading rules configuration.
Rules match positions by symbol pattern and define exit conditions.
Position details (entry price, quantity, etc.) are auto-fetched from account.

:copyright: (c) 2025
:license: MIT
"""

import re
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ConditionType(str, Enum):
    """
    Price condition type enumeration.

    Defines how price targets are calculated relative to entry price.

    :cvar ABSOLUTE: Fixed price target (e.g., 500.0).
    :cvar RELATIVE: Price offset from entry (e.g., +100 points).
    :cvar PERCENTAGE: Percentage of entry price (e.g., 10%).
    """

    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    PERCENTAGE = "percentage"


class OrderType(str, Enum):
    """
    Order type enumeration for exit orders.

    :cvar MARKET: Market order for immediate execution.
    :cvar LIMIT: Limit order at specified price.
    """

    MARKET = "MARKET"
    LIMIT = "LIMIT"


class TakeProfitCondition(BaseModel):
    """
    Take-profit exit condition configuration.

    Defines when and how to take profit on a position.

    :ivar enabled: Whether take-profit is active.
    :ivar condition_type: How to calculate target (absolute/relative/percentage).
    :ivar target: Target value based on condition_type.
    :ivar order_type: Order type to use when triggered.
    :ivar trail: Enable trailing take-profit.
    :ivar trail_step: Step size for trailing (points to give back).
    """

    enabled: bool = True
    condition_type: ConditionType = ConditionType.RELATIVE
    target: float = Field(..., description="Target value")
    order_type: OrderType = OrderType.MARKET
    trail: bool = False
    trail_step: Optional[float] = None


class StopLossCondition(BaseModel):
    """
    Stop-loss exit condition configuration.

    Defines when and how to cut losses on a position.

    :ivar enabled: Whether stop-loss is active.
    :ivar condition_type: How to calculate stop (absolute/relative/percentage).
    :ivar stop: Stop value based on condition_type.
    :ivar order_type: Order type to use when triggered.
    :ivar trail: Enable trailing stop-loss.
    :ivar trail_step: Step size for trailing.
    """

    enabled: bool = True
    condition_type: ConditionType = ConditionType.RELATIVE
    stop: float = Field(..., description="Stop value")
    order_type: OrderType = OrderType.MARKET
    trail: bool = False
    trail_step: Optional[float] = None


class TimeCondition(BaseModel):
    """
    Time-based trading conditions.

    Defines time windows for trading activity and auto square-off.

    :ivar start_time: Start of trading window (HH:MM format).
    :ivar end_time: End of trading window (HH:MM format).
    :ivar square_off_time: Time to force close positions (HH:MM format).
    :ivar active_days: List of active weekdays (0=Monday, 4=Friday).
    """

    start_time: str = "09:15"
    end_time: str = "15:15"
    square_off_time: Optional[str] = "15:20"
    active_days: List[int] = Field(default=[0, 1, 2, 3, 4])


class ExitRule(BaseModel):
    """
    Exit rule matched to positions by symbol pattern.

    Defines exit conditions (TP/SL) for positions matching a pattern.
    Patterns support exact match, wildcards, and regex.

    :ivar rule_id: Unique identifier for the rule.
    :ivar name: Human-readable rule name.
    :ivar enabled: Whether the rule is active.
    :ivar symbol_pattern: Pattern to match trading symbols.
    :ivar exchange: Exchange filter (NFO, BFO, etc.) or None for all.
    :ivar apply_to: Position type filter (LONG, SHORT, or ALL).
    :ivar take_profit: Take-profit condition configuration.
    :ivar stop_loss: Stop-loss condition configuration.
    :ivar time_conditions: Time-based conditions.
    :ivar tags: List of tags for categorization.
    :ivar notes: Optional notes about the rule.

    Pattern formats:
        - Exact: ``"SENSEX24N2779000CE"``
        - Wildcard: ``"SENSEX*CE"``, ``"NIFTY*"``
        - Regex: ``"^SENSEX.*CE$"``

    Example::

        rule = ExitRule(
            rule_id="sensex-options",
            name="SENSEX Options",
            symbol_pattern="SENSEX*",
            exchange="BFO",
            take_profit=TakeProfitCondition(target=100),
            stop_loss=StopLossCondition(stop=40),
        )
    """

    rule_id: str
    name: str
    enabled: bool = True
    symbol_pattern: str = Field(..., description="Pattern to match (wildcards: * ?)")
    exchange: Optional[str] = None
    apply_to: str = Field(default="ALL", pattern="^(LONG|SHORT|ALL)$")
    take_profit: Optional[TakeProfitCondition] = None
    stop_loss: Optional[StopLossCondition] = None
    time_conditions: Optional[TimeCondition] = None
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

    def matches(
        self, symbol: str, exchange: Optional[str] = None, position_type: str = "LONG"
    ) -> bool:
        """
        Check if this rule matches a position.

        :param symbol: The trading symbol to match.
        :type symbol: str
        :param exchange: The exchange name (optional).
        :type exchange: Optional[str]
        :param position_type: Position type (LONG or SHORT).
        :type position_type: str
        :returns: True if the rule matches, False otherwise.
        :rtype: bool

        Example::

            if rule.matches("SENSEX25D0486000CE", "BFO", "LONG"):
                print("Rule matched!")
        """
        if self.exchange and exchange and self.exchange != exchange:
            return False
        if self.apply_to != "ALL" and self.apply_to != position_type:
            return False
        pattern = self.symbol_pattern
        if "*" in pattern or "?" in pattern:
            regex = pattern.replace("*", ".*").replace("?", ".")
            regex = f"^{regex}$"
        else:
            regex = f"^{re.escape(pattern)}$"

        try:
            return bool(re.match(regex, symbol, re.IGNORECASE))
        except:
            return False

    def calc_tp(self, entry_price: float, position_type: str) -> Optional[float]:
        """
        Calculate the take-profit trigger price.

        :param entry_price: The entry price of the position.
        :type entry_price: float
        :param position_type: Position type (LONG or SHORT).
        :type position_type: str
        :returns: The calculated TP price, or None if TP is disabled.
        :rtype: Optional[float]

        Example::

            tp_price = rule.calc_tp(entry_price=366.0, position_type="LONG")
        """
        if not self.take_profit or not self.take_profit.enabled:
            return None

        tp = self.take_profit
        if tp.condition_type == ConditionType.ABSOLUTE:
            return tp.target
        elif tp.condition_type == ConditionType.RELATIVE:
            return (
                entry_price + tp.target
                if position_type == "LONG"
                else entry_price - tp.target
            )
        elif tp.condition_type == ConditionType.PERCENTAGE:
            mult = (
                1 + tp.target / 100 if position_type == "LONG" else 1 - tp.target / 100
            )
            return entry_price * mult
        return None

    def calc_sl(self, entry_price: float, position_type: str) -> Optional[float]:
        """
        Calculate the stop-loss trigger price.

        :param entry_price: The entry price of the position.
        :type entry_price: float
        :param position_type: Position type (LONG or SHORT).
        :type position_type: str
        :returns: The calculated SL price, or None if SL is disabled.
        :rtype: Optional[float]

        Example::

            sl_price = rule.calc_sl(entry_price=366.0, position_type="LONG")
        """
        if not self.stop_loss or not self.stop_loss.enabled:
            return None

        sl = self.stop_loss
        if sl.condition_type == ConditionType.ABSOLUTE:
            return sl.stop
        elif sl.condition_type == ConditionType.RELATIVE:
            return (
                entry_price - sl.stop
                if position_type == "LONG"
                else entry_price + sl.stop
            )
        elif sl.condition_type == ConditionType.PERCENTAGE:
            mult = 1 - sl.stop / 100 if position_type == "LONG" else 1 + sl.stop / 100
            return entry_price * mult
        return None

    def check_tp(self, price: float, entry: float, pos_type: str) -> bool:
        """
        Check if take-profit should trigger at the current price.

        :param price: Current market price.
        :type price: float
        :param entry: Entry price of the position.
        :type entry: float
        :param pos_type: Position type (LONG or SHORT).
        :type pos_type: str
        :returns: True if TP should trigger, False otherwise.
        :rtype: bool

        Example::

            if rule.check_tp(price=470.0, entry=366.0, pos_type="LONG"):
                print("Take profit triggered!")
        """
        tp = self.calc_tp(entry, pos_type)
        if tp is None:
            return False
        return price >= tp if pos_type == "LONG" else price <= tp

    def check_sl(self, price: float, entry: float, pos_type: str) -> bool:
        """
        Check if stop-loss should trigger at the current price.

        :param price: Current market price.
        :type price: float
        :param entry: Entry price of the position.
        :type entry: float
        :param pos_type: Position type (LONG or SHORT).
        :type pos_type: str
        :returns: True if SL should trigger, False otherwise.
        :rtype: bool

        Example::

            if rule.check_sl(price=320.0, entry=366.0, pos_type="LONG"):
                print("Stop loss triggered!")
        """
        sl = self.calc_sl(entry, pos_type)
        if sl is None:
            return False
        return price <= sl if pos_type == "LONG" else price >= sl


class DefaultConditions(BaseModel):
    """
    Default exit conditions applied when no specific rule matches.

    :ivar enabled: Whether default conditions are active.
    :ivar take_profit: Default take-profit configuration.
    :ivar stop_loss: Default stop-loss configuration.
    """

    enabled: bool = False
    take_profit: Optional[TakeProfitCondition] = None
    stop_loss: Optional[StopLossCondition] = None


class TradingConfig(BaseModel):
    """
    Root configuration model for trading rules.

    Contains all rules and default settings loaded from YAML.

    :ivar version: Configuration schema version.
    :ivar defaults: Default conditions for unmatched positions.
    :ivar default_time_conditions: Default time conditions.
    :ivar rules: List of exit rules.

    Example::

        config = TradingConfig(
            version="2.0",
            rules=[rule1, rule2],
        )
    """

    version: str = "2.0"
    defaults: Optional[DefaultConditions] = None
    default_time_conditions: Optional[TimeCondition] = None
    rules: List[ExitRule] = Field(default_factory=list)

    def find_rule(
        self, symbol: str, exchange: str, pos_type: str
    ) -> Optional[ExitRule]:
        """
        Find the first matching enabled rule for a position.

        :param symbol: The trading symbol.
        :type symbol: str
        :param exchange: The exchange name.
        :type exchange: str
        :param pos_type: Position type (LONG or SHORT).
        :type pos_type: str
        :returns: The matching rule, or None if no match.
        :rtype: Optional[ExitRule]

        Example::

            rule = config.find_rule("SENSEX25D0486000CE", "BFO", "LONG")
        """
        for rule in self.rules:
            if rule.enabled and rule.matches(symbol, exchange, pos_type):
                return rule
        return None

    def get_rule(self, rule_id: str) -> Optional[ExitRule]:
        """
        Get a rule by its unique ID.

        :param rule_id: The rule ID to look up.
        :type rule_id: str
        :returns: The rule if found, None otherwise.
        :rtype: Optional[ExitRule]

        Example::

            rule = config.get_rule("sensex-options")
        """
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None
