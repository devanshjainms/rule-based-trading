"""
Tests for Trading Engine.

Tests rule matching, TP/SL calculation, and trigger logic.
"""

import asyncio
import sys

import pytest

sys.path.insert(0, str(__file__).rsplit("/tests", 1)[0])

from src.rules.schema import (
    ConditionType,
    ExitRule,
    StopLossCondition,
    TakeProfitCondition,
    TradingConfig,
)
from src.rules.engine import ActiveTrade, TradingEngine
from src.monitor import TrackedPosition
from tests.mocks import MockKiteClient, MockPosition, MockRulesRepository


class TestExitRule:
    """Tests for ExitRule matching and calculations."""

    def test_exact_match(self):
        """Test exact symbol matching."""
        rule = ExitRule(
            rule_id="test",
            name="Test Rule",
            symbol_pattern="SENSEX25D0486000CE",
        )
        assert rule.matches("SENSEX25D0486000CE") is True
        assert rule.matches("SENSEX25D0486000PE") is False

    def test_wildcard_match(self):
        """Test wildcard pattern matching."""
        rule = ExitRule(
            rule_id="test",
            name="Test Rule",
            symbol_pattern="SENSEX*",
            exchange="BFO",
        )
        assert rule.matches("SENSEX25D0486000CE", "BFO") is True
        assert rule.matches("SENSEX25D0486000PE", "BFO") is True
        assert rule.matches("NIFTY25D0425000CE", "BFO") is False

    def test_exchange_filter(self):
        """Test exchange filtering."""
        rule = ExitRule(
            rule_id="test",
            name="Test Rule",
            symbol_pattern="SENSEX*",
            exchange="BFO",
        )
        assert rule.matches("SENSEX25D0486000CE", "BFO") is True
        assert rule.matches("SENSEX25D0486000CE", "NFO") is False

    def test_position_type_filter(self):
        """Test position type filtering."""
        rule = ExitRule(
            rule_id="test",
            name="Test Rule",
            symbol_pattern="SENSEX*",
            apply_to="LONG",
        )
        assert rule.matches("SENSEX25D0486000CE", position_type="LONG") is True
        assert rule.matches("SENSEX25D0486000CE", position_type="SHORT") is False

    def test_calc_tp_relative_long(self):
        """Test TP calculation with relative condition (LONG)."""
        rule = ExitRule(
            rule_id="test",
            name="Test Rule",
            symbol_pattern="SENSEX*",
            take_profit=TakeProfitCondition(
                enabled=True,
                condition_type=ConditionType.RELATIVE,
                target=100,
            ),
        )
        tp_price = rule.calc_tp(entry_price=366.0, position_type="LONG")
        assert tp_price == 466.0

    def test_calc_tp_relative_short(self):
        """Test TP calculation with relative condition (SHORT)."""
        rule = ExitRule(
            rule_id="test",
            name="Test Rule",
            symbol_pattern="SENSEX*",
            take_profit=TakeProfitCondition(
                enabled=True,
                condition_type=ConditionType.RELATIVE,
                target=100,
            ),
        )
        tp_price = rule.calc_tp(entry_price=400.0, position_type="SHORT")
        assert tp_price == 300.0

    def test_calc_tp_percentage(self):
        """Test TP calculation with percentage condition."""
        rule = ExitRule(
            rule_id="test",
            name="Test Rule",
            symbol_pattern="SENSEX*",
            take_profit=TakeProfitCondition(
                enabled=True,
                condition_type=ConditionType.PERCENTAGE,
                target=30,
            ),
        )
        tp_price = rule.calc_tp(entry_price=100.0, position_type="LONG")
        assert tp_price == 130.0

    def test_calc_sl_relative_long(self):
        """Test SL calculation with relative condition (LONG)."""
        rule = ExitRule(
            rule_id="test",
            name="Test Rule",
            symbol_pattern="SENSEX*",
            stop_loss=StopLossCondition(
                enabled=True,
                condition_type=ConditionType.RELATIVE,
                stop=40,
            ),
        )
        sl_price = rule.calc_sl(entry_price=366.0, position_type="LONG")
        assert sl_price == 326.0

    def test_calc_sl_relative_short(self):
        """Test SL calculation with relative condition (SHORT)."""
        rule = ExitRule(
            rule_id="test",
            name="Test Rule",
            symbol_pattern="SENSEX*",
            stop_loss=StopLossCondition(
                enabled=True,
                condition_type=ConditionType.RELATIVE,
                stop=40,
            ),
        )
        sl_price = rule.calc_sl(entry_price=400.0, position_type="SHORT")
        assert sl_price == 440.0

    def test_check_tp_triggered_long(self):
        """Test TP trigger check for LONG position."""
        rule = ExitRule(
            rule_id="test",
            name="Test Rule",
            symbol_pattern="SENSEX*",
            take_profit=TakeProfitCondition(
                enabled=True,
                condition_type=ConditionType.RELATIVE,
                target=100,
            ),
        )
        assert rule.check_tp(price=470.0, entry=366.0, pos_type="LONG") is True
        assert rule.check_tp(price=460.0, entry=366.0, pos_type="LONG") is False

    def test_check_sl_triggered_long(self):
        """Test SL trigger check for LONG position."""
        rule = ExitRule(
            rule_id="test",
            name="Test Rule",
            symbol_pattern="SENSEX*",
            stop_loss=StopLossCondition(
                enabled=True,
                condition_type=ConditionType.RELATIVE,
                stop=40,
            ),
        )
        assert rule.check_sl(price=320.0, entry=366.0, pos_type="LONG") is True
        assert rule.check_sl(price=330.0, entry=366.0, pos_type="LONG") is False


class TestTradingConfig:
    """Tests for TradingConfig rule finding."""

    def test_find_matching_rule(self):
        """Test finding matching rule for a symbol."""
        config = TradingConfig(
            version="2.0",
            rules=[
                ExitRule(
                    rule_id="sensex",
                    name="SENSEX",
                    symbol_pattern="SENSEX*",
                    exchange="BFO",
                ),
                ExitRule(
                    rule_id="nifty",
                    name="NIFTY",
                    symbol_pattern="NIFTY*",
                    exchange="NFO",
                ),
            ],
        )

        rule = config.find_rule("SENSEX25D0486000CE", "BFO", "LONG")
        assert rule is not None
        assert rule.rule_id == "sensex"

        rule = config.find_rule("NIFTY25NOV24500CE", "NFO", "LONG")
        assert rule is not None
        assert rule.rule_id == "nifty"

        rule = config.find_rule("RELIANCE", "NSE", "LONG")
        assert rule is None


class TestActiveTrade:
    """Tests for ActiveTrade state management."""

    def test_price_tracking(self):
        """Test high/low price tracking."""
        position = TrackedPosition(
            instrument_token=12345,
            trading_symbol="SENSEX25D0486000CE",
            exchange="BFO",
            product="NRML",
            quantity=1000,
            average_price=366.0,
        )
        rule = ExitRule(
            rule_id="test",
            name="Test",
            symbol_pattern="SENSEX*",
        )

        trade = ActiveTrade(
            position=position,
            rule=rule,
            tp_price=466.0,
            sl_price=326.0,
        )

        trade.update_price(370.0)
        assert trade.current_price == 370.0
        assert trade.highest_price == 370.0
        assert trade.lowest_price == 370.0

        trade.update_price(380.0)
        assert trade.current_price == 380.0
        assert trade.highest_price == 380.0
        assert trade.lowest_price == 370.0

        trade.update_price(360.0)
        assert trade.current_price == 360.0
        assert trade.highest_price == 380.0
        assert trade.lowest_price == 360.0


class TestTradingEngine:
    """Tests for TradingEngine."""

    @pytest.fixture
    def engine_setup(self):
        """Set up engine with mocks."""
        client = MockKiteClient()
        rules_repo = MockRulesRepository()
        user_id = "test-user-123"

        rules_repo.set_rules(
            user_id,
            [
                {
                    "id": "sensex-options",
                    "name": "SENSEX Options",
                    "symbol_pattern": "SENSEX*",
                    "exchange": "BFO",
                    "position_type": None,
                    "is_active": True,
                    "take_profit": {
                        "enabled": True,
                        "condition_type": "relative",
                        "target": 100,
                    },
                    "stop_loss": {
                        "enabled": True,
                        "condition_type": "relative",
                        "stop": 40,
                    },
                    "time_conditions": {},
                }
            ],
        )

        return {
            "client": client,
            "rules_repo": rules_repo,
            "user_id": user_id,
        }

    @pytest.mark.asyncio
    async def test_position_matched_to_rule(self, engine_setup):
        """Test that new position gets matched to correct rule."""
        client = engine_setup["client"]
        rules_repo = engine_setup["rules_repo"]
        user_id = engine_setup["user_id"]

        triggered_trades = []

        async def on_trigger(trade, trigger_type):
            triggered_trades.append((trade, trigger_type))

        engine = TradingEngine(
            kite_client=client,
            rules_repository=rules_repo,
            user_id=user_id,
            ticker_client=None,
            on_trigger=on_trigger,
            position_poll_interval=0.05,
            price_poll_interval=0.05,
        )

        await engine.start()

        client.add_position(
            MockPosition(
                tradingsymbol="SENSEX25D0486000CE",
                exchange="BFO",
                quantity=1000,
                average_price=366.0,
                last_price=370.0,
                instrument_token=289987077,
            )
        )

        await asyncio.sleep(0.2)

        active = engine.get_active_trades()
        assert len(active) == 1
        assert active[0]["symbol"] == "SENSEX25D0486000CE"
        assert active[0]["tp_price"] == 466.0
        assert active[0]["sl_price"] == 326.0

        await engine.stop()

    @pytest.mark.asyncio
    async def test_tp_trigger(self, engine_setup):
        """Test take-profit trigger."""
        client = engine_setup["client"]
        rules_repo = engine_setup["rules_repo"]
        user_id = engine_setup["user_id"]

        triggered_trades = []

        async def on_trigger(trade, trigger_type):
            triggered_trades.append((trade, trigger_type))

        engine = TradingEngine(
            kite_client=client,
            rules_repository=rules_repo,
            user_id=user_id,
            ticker_client=None,
            on_trigger=on_trigger,
            position_poll_interval=0.05,
            price_poll_interval=0.05,
        )

        await engine.start()

        client.add_position(
            MockPosition(
                tradingsymbol="SENSEX25D0486000CE",
                exchange="BFO",
                quantity=1000,
                average_price=366.0,
                last_price=366.0,
                instrument_token=289987077,
            )
        )

        await asyncio.sleep(0.2)

        client.update_ltp("SENSEX25D0486000CE", "BFO", 470.0)
        await asyncio.sleep(0.15)

        await engine.stop()

        assert len(triggered_trades) == 1
        assert triggered_trades[0][1] == "TP"

    @pytest.mark.asyncio
    async def test_sl_trigger(self, engine_setup):
        """Test stop-loss trigger."""
        client = engine_setup["client"]
        rules_repo = engine_setup["rules_repo"]
        user_id = engine_setup["user_id"]

        triggered_trades = []

        async def on_trigger(trade, trigger_type):
            triggered_trades.append((trade, trigger_type))

        engine = TradingEngine(
            kite_client=client,
            rules_repository=rules_repo,
            user_id=user_id,
            ticker_client=None,
            on_trigger=on_trigger,
            position_poll_interval=0.05,
            price_poll_interval=0.05,
        )

        await engine.start()

        client.add_position(
            MockPosition(
                tradingsymbol="SENSEX25D0486000CE",
                exchange="BFO",
                quantity=1000,
                average_price=366.0,
                last_price=366.0,
                instrument_token=289987077,
            )
        )

        await asyncio.sleep(0.2)

        client.update_ltp("SENSEX25D0486000CE", "BFO", 320.0)
        await asyncio.sleep(0.15)

        await engine.stop()

        assert len(triggered_trades) == 1
        assert triggered_trades[0][1] == "SL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
