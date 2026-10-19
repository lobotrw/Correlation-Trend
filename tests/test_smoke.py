"""Smoke tests. test_each_coin needs network (Yahoo Finance fallback; no API key used)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
COINS = ("BTC", "ETH", "BNB", "ADA", "SOL", "XRP", "DOT", "DOGE", "UNI", "LTC")


@pytest.mark.parametrize("coin", COINS)
def test_each_coin(coin, monkeypatch):
    monkeypatch.chdir(ROOT)
    monkeypatch.delenv("CRYPTOCOMPARE_API_KEY", raising=False)
    at = AppTest.from_file(str(ROOT / "main.py"), default_timeout=300)
    at.run()
    at.selectbox[0].set_value(coin).run()
    assert not at.exception, [e.message for e in at.exception]
    assert -1 <= float(at.metric[0].value) <= 1


def test_no_data_shows_error_not_crash():
    at = AppTest.from_file(str(ROOT / "tests" / "no_data_app.py"), default_timeout=120)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.error
