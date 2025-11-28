"""
Trading Rules Module.

Provides rule-based exit conditions for positions.

:copyright: (c) 2025
:license: MIT
"""

from .schema import (
    TradingConfig,
    ExitRule,
    TakeProfitCondition,
    StopLossCondition,
    TimeCondition,
    ConditionType,
    OrderType,
    DefaultConditions,
)
from .parser import RulesParser, get_parser
from .engine import TradingEngine, ActiveTrade

__all__ = [
    "TradingConfig",
    "ExitRule",
    "TakeProfitCondition",
    "StopLossCondition",
    "TimeCondition",
    "ConditionType",
    "OrderType",
    "DefaultConditions",
    "RulesParser",
    "get_parser",
    "TradingEngine",
    "ActiveTrade",
]
