"""
Trading utility functions for risk management and order validation.

This module provides essential utility functions for:
- Risk calculation and management
- Order parameter validation
- Position value calculations

All monetary calculations use Decimal for precise floating-point arithmetic.
"""

from typing import Dict, Union
from decimal import Decimal

def calculate_risk(position_size: Union[int, float], risk_percent: float) -> float:
    """
    Calculate the risk amount for a given position size and risk percentage.
    
    This function helps determine the maximum loss amount you're willing to accept
    for a given position. It uses Decimal for precise calculations to avoid
    floating-point errors in financial calculations.
    
    Args:
        position_size: The size of the position in currency units (e.g., 10000 for ₹10,000)
        risk_percent: The risk percentage as a float (e.g., 2.0 for 2%)
        
    Returns:
        float: The risk amount in currency units
        
    Examples:
        >>> calculate_risk(10000, 2.0)
        200.0  # ₹200 risk on ₹10,000 position at 2% risk
        
        >>> calculate_risk(50000, 1.5)
        750.0  # ₹750 risk on ₹50,000 position at 1.5% risk
    """
    return float(Decimal(str(position_size)) * Decimal(str(risk_percent)) / Decimal('100'))

def validate_order_params(params: Dict) -> bool:
    """
    Validate order parameters before submission to prevent invalid orders.
    
    This function checks for the presence of all required fields in the order
    parameters. It does not validate the values themselves, only their presence.
    
    Args:
        params: Dictionary containing order parameters with the following required keys:
            - tradingsymbol: The trading symbol (e.g., "RELIANCE")
            - quantity: Number of units to trade
            - transaction_type: "BUY" or "SELL"
            - order_type: "MARKET", "LIMIT", etc.
        
    Returns:
        bool: True if all required parameters are present, False otherwise
        
    Examples:
        >>> params = {
        ...     "tradingsymbol": "RELIANCE",
        ...     "quantity": 1,
        ...     "transaction_type": "BUY",
        ...     "order_type": "MARKET"
        ... }
        >>> validate_order_params(params)
        True
        
        >>> incomplete_params = {"tradingsymbol": "RELIANCE"}
        >>> validate_order_params(incomplete_params)
        False
    """
    required_fields = {
        'tradingsymbol',
        'quantity',
        'transaction_type',
        'order_type'
    }
    
    return all(field in params for field in required_fields)

def calculate_position_value(quantity: int, price: float) -> float:
    """
    Calculate the total value of a position based on quantity and price.
    
    This function uses Decimal for precise multiplication of quantity and price
    to avoid floating-point errors in financial calculations.
    
    Args:
        quantity: Number of units in the position (e.g., number of shares)
        price: Price per unit (e.g., price per share)
        
    Returns:
        float: Total position value (quantity * price)
        
    Examples:
        >>> calculate_position_value(100, 1550.75)
        155075.0  # Value of 100 shares at ₹1,550.75 each
        
        >>> calculate_position_value(50, 2420.50)
        121025.0  # Value of 50 shares at ₹2,420.50 each
    """
    return float(Decimal(str(quantity)) * Decimal(str(price))) 