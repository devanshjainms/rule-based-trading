"""
Pytest fixtures for testing.

:copyright: (c) 2025
:license: MIT
"""

import pytest
import tempfile
import os
from pathlib import Path

from .mocks import MockKiteClient, MockTickerClient, MockPosition


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
def rules_yaml_content():
    """
    Sample rules YAML content.

    :returns: YAML string with sample trading rules.
    :rtype: str
    """
    return """
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

  - rule_id: "nifty-options"
    name: "NIFTY Options"
    symbol_pattern: "NIFTY*"
    exchange: "NFO"
    apply_to: "ALL"

    take_profit:
      enabled: true
      condition_type: percentage
      target: 30
      order_type: MARKET

    stop_loss:
      enabled: true
      condition_type: percentage
      stop: 20
      order_type: MARKET
"""


@pytest.fixture
def rules_file(rules_yaml_content, tmp_path):
    """
    Create a temporary rules file.

    :param rules_yaml_content: YAML content for rules file.
    :type rules_yaml_content: str
    :param tmp_path: Pytest temporary path fixture.
    :type tmp_path: Path
    :returns: Path to temporary rules file.
    :rtype: str
    """
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(rules_yaml_content)
    return str(rules_path)


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
    return mock_client
