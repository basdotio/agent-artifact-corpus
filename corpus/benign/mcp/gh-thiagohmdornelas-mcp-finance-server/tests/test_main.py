from unittest.mock import MagicMock

import pytest

import main


@pytest.fixture
def fake_ticker(monkeypatch):
    ticker = MagicMock()
    ticker.fast_info = {'lastPrice': 123.45}
    ticker.history.return_value.to_dict.return_value = {'Close': {0: 1.0}}
    ticker.info = {'shortName': 'Apple Inc.'}
    monkeypatch.setattr(main.yf, 'Ticker', lambda symbol: ticker)
    return ticker


def test_get_current_stock_price(fake_ticker):
    assert main.get_current_stock_price('AAPL') == 123.45


def test_get_history_stock_price(fake_ticker):
    resultado = main.get_history_stock_price('AAPL', '1mo')
    assert resultado == {'Close': {0: 1.0}}


def test_get_company_info(fake_ticker):
    assert main.get_company_info('AAPL') == {'shortName': 'Apple Inc.'}
