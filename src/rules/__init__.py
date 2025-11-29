"""
Trading Rules Module.

Provides rule-based exit conditions for positions.

:copyright: (c) 2025
:license: MIT
"""

from .schema import (
    ConditionType,
    DefaultConditions,
    ExitRule,
    OrderType,
    StopLossCondition,
    TakeProfitCondition,
    TimeCondition,
    TradingConfig,
)
from .engine import ActiveTrade, TradingEngine

__all__ = [
    "TradingConfig",
    "ExitRule",
    "TakeProfitCondition",
    "StopLossCondition",
    "TimeCondition",
    "ConditionType",
    "OrderType",
    "DefaultConditions",
    "TradingEngine",
    "ActiveTrade",
]
