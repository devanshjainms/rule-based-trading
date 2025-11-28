"""
Tests for PositionMonitor.

Tests position detection, callbacks, and polling behavior.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

import sys

sys.path.insert(0, str(__file__).rsplit("/tests", 1)[0])

from src.monitor import PositionMonitor, TrackedPosition
from tests.mocks import MockKiteClient, MockPosition


class TestTrackedPosition:
    """Tests for TrackedPosition dataclass."""

    def test_position_type_long(self):
        """Test LONG position detection."""
        pos = TrackedPosition(
            instrument_token=12345,
            trading_symbol="SENSEX25D0486000CE",
            exchange="BFO",
            product="NRML",
            quantity=1000,
            average_price=366.0,
            buy_quantity=1000,
            buy_price=366.0,
        )
        assert pos.position_type == "LONG"
        assert pos.entry_price == 366.0
        assert pos.abs_quantity == 1000

    def test_position_type_short(self):
        """Test SHORT position detection."""
        pos = TrackedPosition(
            instrument_token=12345,
            trading_symbol="SENSEX25D0486000CE",
            exchange="BFO",
            product="NRML",
            quantity=-500,
            average_price=400.0,
            sell_quantity=500,
            sell_price=400.0,
        )
        assert pos.position_type == "SHORT"
        assert pos.entry_price == 400.0
        assert pos.abs_quantity == 500

    def test_position_type_flat(self):
        """Test FLAT position (squared off)."""
        pos = TrackedPosition(
            instrument_token=12345,
            trading_symbol="SENSEX25D0486000CE",
            exchange="BFO",
            product="NRML",
            quantity=0,
            average_price=0,
        )
        assert pos.position_type == "FLAT"

    def test_symbol_key(self):
        """Test symbol key generation."""
        pos = TrackedPosition(
            instrument_token=12345,
            trading_symbol="SENSEX25D0486000CE",
            exchange="BFO",
            product="NRML",
            quantity=100,
            average_price=366.0,
        )
        assert pos.symbol_key == "BFO:SENSEX25D0486000CE"


class TestPositionMonitor:
    """Tests for PositionMonitor class."""

    @pytest.fixture
    def monitor(self):
        """Create a position monitor with mock client."""
        client = MockKiteClient()
        return PositionMonitor(
            kite_client=client,
            poll_interval=0.1,
        )

    def test_parse_position(self, monitor):
        """Test parsing position from API response."""
        pos_data = {
            "instrument_token": 289987077,
            "tradingsymbol": "SENSEX25D0486000CE",
            "exchange": "BFO",
            "product": "NRML",
            "quantity": 1000,
            "average_price": 366.44,
            "last_price": 370.0,
            "pnl": 3560.0,
            "buy_quantity": 1000,
            "sell_quantity": 0,
            "buy_price": 366.44,
            "sell_price": 0,
            "multiplier": 1,
        }

        pos = monitor._parse_position(pos_data)

        assert pos.trading_symbol == "SENSEX25D0486000CE"
        assert pos.exchange == "BFO"
        assert pos.quantity == 1000
        assert pos.position_type == "LONG"
        assert pos.entry_price == 366.44

    @pytest.mark.asyncio
    async def test_new_position_callback(self):
        """Test that new position triggers callback."""
        client = MockKiteClient()
        callback_received = []

        def on_new_position(pos):
            callback_received.append(pos)

        monitor = PositionMonitor(
            kite_client=client,
            poll_interval=0.05,
            on_new_position=on_new_position,
        )

        await monitor.start()

        client.add_position(
            MockPosition(
                tradingsymbol="SENSEX25D0486000CE",
                exchange="BFO",
                quantity=1000,
                average_price=366.0,
                last_price=370.0,
            )
        )

        await asyncio.sleep(0.15)

        await monitor.stop()

        assert len(callback_received) == 1
        assert callback_received[0].trading_symbol == "SENSEX25D0486000CE"
        assert callback_received[0].position_type == "LONG"

    @pytest.mark.asyncio
    async def test_position_closed_callback(self):
        """Test that closing position triggers callback."""
        client = MockKiteClient()

        client.add_position(
            MockPosition(
                tradingsymbol="SENSEX25D0486000CE",
                exchange="BFO",
                quantity=1000,
                average_price=366.0,
                last_price=370.0,
            )
        )

        closed_positions = []

        def on_position_closed(pos):
            closed_positions.append(pos)

        monitor = PositionMonitor(
            kite_client=client,
            poll_interval=0.05,
            on_position_closed=on_position_closed,
        )

        await monitor.start()
        await asyncio.sleep(0.1)

        client.close_position("SENSEX25D0486000CE")

        await asyncio.sleep(0.15)

        await monitor.stop()

        assert len(closed_positions) == 1
        assert closed_positions[0].trading_symbol == "SENSEX25D0486000CE"

    @pytest.mark.asyncio
    async def test_no_callback_for_flat_positions(self):
        """Test that flat positions don't trigger new position callback."""
        client = MockKiteClient()

        client.add_position(
            MockPosition(
                tradingsymbol="SENSEX25D0486000CE",
                exchange="BFO",
                quantity=0,
                average_price=0,
                last_price=370.0,
            )
        )

        callback_count = [0]

        def on_new_position(pos):
            callback_count[0] += 1

        monitor = PositionMonitor(
            kite_client=client,
            poll_interval=0.05,
            on_new_position=on_new_position,
        )

        await monitor.start()
        await asyncio.sleep(0.15)
        await monitor.stop()

        assert callback_count[0] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
