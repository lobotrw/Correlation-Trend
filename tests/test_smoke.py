"""Smoke tests. test_each_coin needs network (Yahoo Finance fallback; no API key used)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_each_coin(monkeypatch):
    monkeypatch.chdir(ROOT)
    monkeypatch.delenv("CRYPTOCOMPARE_API_KEY", raising=False)
    at = AppTest.from_file(str(ROOT / "main.py"), default_timeout=300)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    coins = at.selectbox[0].options
    assert "BTC" in coins and len(coins) == 10
    for coin in coins:
        at.selectbox[0].set_value(coin).run()
        assert not at.exception, (coin, [e.message for e in at.exception])
        for m in at.metric:
            assert -1 <= float(m.value) <= 1
        table = at.dataframe[0].value
        assert table["Return corr. with BTC"].between(-1, 1).all()


def test_no_data_shows_error_not_crash():
    at = AppTest.from_file(str(ROOT / "tests" / "no_data_app.py"), default_timeout=120)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.error
