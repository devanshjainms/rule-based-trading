"""
Integration Test: SENSEX Position Scenario

This test mimics the exact scenario from the screenshot:
- Symbol: SENSEX 4th DEC 86000 CE (SENSEX25D0486000CE)
- Exchange: BFO
- Quantity: 1000 (bought in 4 tranches: 300+300+300+100)
- Avg Entry: ~366.44
- Product: NRML

Rules:
- TP: +100 points → triggers at 466
- SL: -40 points → triggers at 326

Test scenarios:
1. Position is detected and matched to rule
2. TP triggers when price hits 466+
3. SL triggers when price hits 326-
4. SELL order is placed with correct quantity
"""

import pytest
import asyncio
from datetime import datetime
from typing import List, Tuple

import sys

sys.path.insert(0, str(__file__).rsplit("/tests", 1)[0])

from src.rules.schema import (
    ExitRule,
    TakeProfitCondition,
    StopLossCondition,
    ConditionType,
    TradingConfig,
)
from src.rules.parser import RulesParser
from src.rules.engine import TradingEngine, ActiveTrade
from src.monitor import TrackedPosition
from tests.mocks import MockKiteClient, MockTickerClient, MockPosition, MockOrder


class TestSensexScenario:
    """
    Full integration test mimicking the SENSEX position from the screenshot.
    """

    @pytest.fixture
    def setup(self, tmp_path):
        """Set up the test environment."""
        rules_content = """
version: "2.0"

defaults:
  enabled: false

rules:
  - rule_id: "sensex-options"
    name: "SENSEX Options"
    symbol_pattern: "SENSEX*"
    exchange: "BFO"
    apply_to: "ALL"

    take_profit:
      enabled: true
      condition_type: relative
      target: 100
      order_type: MARKET

    stop_loss:
      enabled: true
      condition_type: relative
      stop: 40
      order_type: MARKET
"""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(rules_content)

        client = MockKiteClient()
        parser = RulesParser(str(rules_file))

        return {
            "client": client,
            "ticker": None,
            "parser": parser,
        }

    def create_sensex_position(self, client: MockKiteClient) -> None:
        """
        Create the SENSEX position from screenshot.

        Orders were:
        - 12:34:04 BUY 300 @ 366.44
        - 12:34:34 BUY 300 @ 367.41
        - 12:35:35 BUY 300 @ 371.34
        - 12:37:28 BUY 100 @ 360.55

        Total: 1000 qty, weighted avg ~366.89
        """
        weighted_avg = (
            300 * 366.44 + 300 * 367.41 + 300 * 371.34 + 100 * 360.55
        ) / 1000

        client.add_position(
            MockPosition(
                tradingsymbol="SENSEX25D0486000CE",
                exchange="BFO",
                quantity=1000,
                average_price=round(weighted_avg, 2),
                last_price=370.0,
                product="NRML",
                instrument_token=289987077,
                buy_quantity=1000,
                buy_price=round(weighted_avg, 2),
            )
        )

    def test_position_values(self, setup):
        """Verify position values match screenshot."""
        client = setup["client"]
        self.create_sensex_position(client)

        positions = client.positions()
        pos = positions["net"][0]

        assert pos["tradingsymbol"] == "SENSEX25D0486000CE"
        assert pos["exchange"] == "BFO"
        assert pos["quantity"] == 1000
        assert 366 <= pos["average_price"] <= 368
        assert pos["product"] == "NRML"

    def test_rule_matching(self, setup):
        """Test that SENSEX position matches sensex-options rule."""
        parser = setup["parser"]
        config = parser.load()

        rule = config.find_rule("SENSEX25D0486000CE", "BFO", "LONG")

        assert rule is not None
        assert rule.rule_id == "sensex-options"
        assert rule.take_profit is not None
        assert rule.stop_loss is not None

    def test_tp_sl_calculation(self, setup):
        """Test TP/SL price calculation for the position."""
        parser = setup["parser"]
        config = parser.load()
        rule = config.find_rule("SENSEX25D0486000CE", "BFO", "LONG")

        entry_price = 366.89

        tp_price = rule.calc_tp(entry_price, "LONG")
        sl_price = rule.calc_sl(entry_price, "LONG")

        assert tp_price == pytest.approx(466.89, rel=0.01)

        assert sl_price == pytest.approx(326.89, rel=0.01)

    @pytest.mark.asyncio
    async def test_tp_trigger_scenario(self, setup):
        """
        Test: Price rises to TP → SELL order placed.

        Scenario:
        1. Position detected at entry ~367
        2. Price moves to 470 (crosses TP at ~467)
        3. SELL order for 1000 qty should be placed
        """
        client = setup["client"]
        parser = setup["parser"]

        self.create_sensex_position(client)

        triggered: List[Tuple[ActiveTrade, str]] = []

        async def on_trigger(trade, trigger_type):
            triggered.append((trade, trigger_type))
            client.close_position(trade.position.trading_symbol)

        engine = TradingEngine(
            kite_client=client,
            rules_parser=parser,
            ticker_client=None,
            on_trigger=on_trigger,
            position_poll_interval=0.05,
            price_poll_interval=0.05,
        )

        await engine.start()
        await asyncio.sleep(0.15)

        active = engine.get_active_trades()
        assert len(active) == 1

        client.update_ltp("SENSEX25D0486000CE", "BFO", 470.0)

        await asyncio.sleep(0.15)

        await engine.stop()

        assert len(triggered) == 1
        trade, trigger_type = triggered[0]

        assert trigger_type == "TP"
        assert trade.position.trading_symbol == "SENSEX25D0486000CE"
        assert trade.position.quantity == 1000

        print(f"\n✅ TP TRIGGERED!")
        print(f"   Symbol: {trade.position.trading_symbol}")
        print(f"   Entry: {trade.position.entry_price}")
        print(f"   TP Price: {trade.tp_price}")
        print(f"   Trigger Price: {trade.current_price}")
        print(f"   Quantity: {trade.position.quantity}")

    @pytest.mark.asyncio
    async def test_sl_trigger_scenario(self, setup):
        """
        Test: Price drops to SL → SELL order placed.

        Scenario:
        1. Position detected at entry ~367
        2. Price drops to 320 (crosses SL at ~327)
        3. SELL order for 1000 qty should be placed
        """
        client = setup["client"]
        parser = setup["parser"]

        self.create_sensex_position(client)

        triggered: List[Tuple[ActiveTrade, str]] = []

        async def on_trigger(trade, trigger_type):
            triggered.append((trade, trigger_type))
            client.close_position(trade.position.trading_symbol)

        engine = TradingEngine(
            kite_client=client,
            rules_parser=parser,
            ticker_client=None,
            on_trigger=on_trigger,
            position_poll_interval=0.05,
            price_poll_interval=0.05,
        )

        await engine.start()
        await asyncio.sleep(0.15)

        client.update_ltp("SENSEX25D0486000CE", "BFO", 320.0)

        await asyncio.sleep(0.15)

        await engine.stop()

        assert len(triggered) == 1
        trade, trigger_type = triggered[0]

        assert trigger_type == "SL"
        assert trade.position.trading_symbol == "SENSEX25D0486000CE"

        print(f"\n✅ SL TRIGGERED!")
        print(f"   Symbol: {trade.position.trading_symbol}")
        print(f"   Entry: {trade.position.entry_price}")
        print(f"   SL Price: {trade.sl_price}")
        print(f"   Trigger Price: {trade.current_price}")

    @pytest.mark.asyncio
    async def test_no_trigger_in_range(self, setup):
        """
        Test: Price stays between SL and TP → no trigger.

        Scenario:
        1. Position at entry ~367
        2. Price stays at 380 (above SL ~327, below TP ~467)
        3. No order should be placed
        """
        client = setup["client"]
        parser = setup["parser"]

        self.create_sensex_position(client)

        triggered = []

        async def on_trigger(trade, trigger_type):
            triggered.append((trade, trigger_type))

        engine = TradingEngine(
            kite_client=client,
            rules_parser=parser,
            ticker_client=None,
            on_trigger=on_trigger,
            position_poll_interval=0.05,
            price_poll_interval=0.05,
        )

        await engine.start()
        await asyncio.sleep(0.15)

        client.update_ltp("SENSEX25D0486000CE", "BFO", 380.0)

        await asyncio.sleep(0.2)

        await engine.stop()

        assert len(triggered) == 0
        print("\n✅ No false triggers - price stayed in range")

    @pytest.mark.asyncio
    async def test_full_order_flow(self, setup):
        """
        Test complete order flow: Detection → Monitoring → Trigger → Order Placed.

        This verifies the actual SELL order would be placed correctly.
        """
        client = setup["client"]
        parser = setup["parser"]

        self.create_sensex_position(client)

        orders_placed = []

        async def on_trigger(trade, trigger_type):
            order_id = client.place_order(
                variety="regular",
                exchange=trade.position.exchange,
                tradingsymbol=trade.position.trading_symbol,
                transaction_type="SELL",
                quantity=trade.position.abs_quantity,
                product=trade.position.product,
                order_type="MARKET",
                tag=f"{trigger_type}_{trade.rule.rule_id[:8]}",
            )
            orders_placed.append(order_id)

        engine = TradingEngine(
            kite_client=client,
            rules_parser=parser,
            ticker_client=None,
            on_trigger=on_trigger,
            position_poll_interval=0.05,
            price_poll_interval=0.05,
        )

        await engine.start()
        await asyncio.sleep(0.15)

        client.update_ltp("SENSEX25D0486000CE", "BFO", 470.0)
        await asyncio.sleep(0.15)

        await engine.stop()

        assert len(orders_placed) == 1

        orders = client.get_placed_orders()
        assert len(orders) == 1

        order = orders[0]
        assert order.tradingsymbol == "SENSEX25D0486000CE"
        assert order.exchange == "BFO"
        assert order.transaction_type == "SELL"
        assert order.quantity == 1000
        assert order.order_type == "MARKET"
        assert order.product == "NRML"
        assert "TP_" in order.tag

        print(f"\n✅ EXIT ORDER PLACED!")
        print(f"   Order ID: {order.order_id}")
        print(f"   Type: {order.transaction_type}")
        print(f"   Symbol: {order.tradingsymbol}")
        print(f"   Quantity: {order.quantity}")
        print(f"   Order Type: {order.order_type}")
        print(f"   Tag: {order.tag}")


class TestMultiplePositions:
    """Test handling multiple positions simultaneously."""

    @pytest.fixture
    def setup_multi(self, tmp_path):
        """Set up with multiple rules."""
        rules_content = """
version: "2.0"

rules:
  - rule_id: "sensex-options"
    name: "SENSEX Options"
    symbol_pattern: "SENSEX*"
    exchange: "BFO"
    take_profit:
      enabled: true
      condition_type: relative
      target: 100
    stop_loss:
      enabled: true
      condition_type: relative
      stop: 40

  - rule_id: "nifty-options"
    name: "NIFTY Options"
    symbol_pattern: "NIFTY*"
    exchange: "NFO"
    take_profit:
      enabled: true
      condition_type: percentage
      target: 30
    stop_loss:
      enabled: true
      condition_type: percentage
      stop: 20
"""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(rules_content)

        client = MockKiteClient()
        parser = RulesParser(str(rules_file))

        return {"client": client, "parser": parser}

    @pytest.mark.asyncio
    async def test_multiple_positions_tracked(self, setup_multi):
        """Test that multiple positions are tracked independently."""
        client = setup_multi["client"]
        parser = setup_multi["parser"]

        client.add_position(
            MockPosition(
                tradingsymbol="SENSEX25D0486000CE",
                exchange="BFO",
                quantity=1000,
                average_price=366.0,
                last_price=370.0,
                instrument_token=100001,
            )
        )

        client.add_position(
            MockPosition(
                tradingsymbol="NIFTY25NOV24500CE",
                exchange="NFO",
                quantity=500,
                average_price=200.0,
                last_price=210.0,
                instrument_token=100002,
            )
        )

        triggers = []

        async def on_trigger(trade, trigger_type):
            triggers.append((trade.position.trading_symbol, trigger_type))

        engine = TradingEngine(
            kite_client=client,
            rules_parser=parser,
            ticker_client=None,
            on_trigger=on_trigger,
            position_poll_interval=0.05,
            price_poll_interval=0.05,
        )

        await engine.start()
        await asyncio.sleep(0.2)

        active = engine.get_active_trades()
        assert len(active) == 2

        client.update_ltp("SENSEX25D0486000CE", "BFO", 470.0)
        await asyncio.sleep(0.15)

        client.update_ltp("NIFTY25NOV24500CE", "NFO", 150.0)
        await asyncio.sleep(0.15)

        await engine.stop()

        assert len(triggers) == 2
        assert ("SENSEX25D0486000CE", "TP") in triggers
        assert ("NIFTY25NOV24500CE", "SL") in triggers

        print("\n✅ Multiple positions handled correctly!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
