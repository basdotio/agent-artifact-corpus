"""
Pytest configuration and fixtures.
"""

import pytest
import yaml
from pathlib import Path

@pytest.fixture
def config():
    """Load test configuration."""
    config_path = Path("config/default.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)

@pytest.fixture
def mock_api_client():
    """Create a mock API client for testing."""
    class MockApiClient:
        def __init__(self):
            self.calls = []
        
        def place_order(self, *args, **kwargs):
            self.calls.append(("place_order", args, kwargs))
            return {"order_id": "TEST123"}
    
    return MockApiClient() 