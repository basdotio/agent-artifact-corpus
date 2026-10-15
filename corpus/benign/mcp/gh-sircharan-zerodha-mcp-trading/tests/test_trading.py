"""
Tests for the trading module.
"""

import pytest
from zerodha_mcp.trading import utils

def test_risk_calculation():
    """Test risk calculation utilities."""
    position_size = 10000
    risk_percent = 2.0
    expected_risk = 200
    
    assert utils.calculate_risk(position_size, risk_percent) == expected_risk

def test_mock_order_placement(mock_api_client):
    """Test order placement with mock client."""
    order_params = {
        "tradingsymbol": "INFY",
        "quantity": 1,
        "price": 1000,
        "transaction_type": "BUY",
        "order_type": "LIMIT"
    }
    
    result = mock_api_client.place_order(**order_params)
    assert result["order_id"] == "TEST123"
    assert len(mock_api_client.calls) == 1
    assert mock_api_client.calls[0][0] == "place_order" 