"""
Pytest fixtures for testing.

:copyright: (c) 2025
:license: MIT
"""

import pytest

from .mocks import MockKiteClient, MockPosition, MockRulesRepository, MockTickerClient


@pytest.fixture
def mock_client():
    """
    Create a mock Kite client.

    :returns: Mock Kite client instance.
    :rtype: MockKiteClient
    """
    return MockKiteClient()


@pytest.fixture
def mock_ticker():
    """
    Create a mock ticker client.

    :returns: Mock ticker client instance.
    :rtype: MockTickerClient
    """
    return MockTickerClient()


@pytest.fixture
def mock_rules_repo():
    """
    Create a mock rules repository.

    :returns: Mock rules repository instance.
    :rtype: MockRulesRepository
    """
    return MockRulesRepository()


@pytest.fixture
def sample_position():
    """
    Create a sample SENSEX position (like the screenshot).

    :returns: Mock position for SENSEX options.
    :rtype: MockPosition
    """
    return MockPosition(
        tradingsymbol="SENSEX25D0486000CE",
        exchange="BFO",
        quantity=1000,
        average_price=366.44,
        last_price=370.0,
        product="NRML",
        instrument_token=289987077,
        buy_quantity=1000,
        buy_price=366.44,
    )


@pytest.fixture
def sample_rules():
    """
    Sample rules configuration for database.

    :returns: List of rule dictionaries.
    :rtype: list
    """
    return [
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
        },
        {
            "id": "nifty-options",
            "name": "NIFTY Options",
            "symbol_pattern": "NIFTY*",
            "exchange": "NFO",
            "position_type": None,
            "is_active": True,
            "take_profit": {
                "enabled": True,
                "condition_type": "percentage",
                "target": 30,
            },
            "stop_loss": {
                "enabled": True,
                "condition_type": "percentage",
                "stop": 20,
            },
            "time_conditions": {},
        },
    ]


@pytest.fixture
def mock_client_with_position(mock_client, sample_position):
    """
    Mock client with a pre-loaded position.

    :param mock_client: Mock Kite client fixture.
    :type mock_client: MockKiteClient
    :param sample_position: Sample position fixture.
    :type sample_position: MockPosition
    :returns: Mock client with position added.
    :rtype: MockKiteClient
    """
    mock_client.add_position(sample_position)
    return mock_client
