"""Offline unit tests for functions.py (no network)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import functions as f  # noqa: E402


def frame(close):
    d = pd.DataFrame({"close": close}, index=pd.date_range("2025-01-01", periods=len(close)))
    d["SMA_25"] = d["close"].rolling(25).mean()
    return d


def test_correlation_uses_returns_not_levels():
    rng = np.random.default_rng(0)
    n = 300
    trend = np.linspace(0, 1, n)
    a = 100 * np.exp(trend + np.cumsum(rng.normal(0, 0.01, n)))      # independent noise,
    b = 50 * np.exp(trend + np.cumsum(rng.normal(0, 0.01, n)))       # common trend only
    px = pd.DataFrame({"A": a, "B": b})
    assert px.corr().loc["A", "B"] > 0.8                             # spurious level correlation
    assert abs(f.return_correlation(px).loc["A", "B"]) < 0.2


def test_trend_up_down_flat():
    up = frame(np.linspace(100, 200, 100))
    down = frame(np.linspace(200, 100, 100))
    flat = frame(np.full(100, 100.0))
    assert f.get_trend_val(up).iloc[-1] == 1
    assert f.get_trend_val(down).iloc[-1] == -1
    assert f.get_trend_val(flat).iloc[-1] == 0


def test_trend_has_no_lookahead():
    rng = np.random.default_rng(3)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 300)))
    full = f.get_trend_val(frame(close)).to_numpy()
    part = f.get_trend_val(frame(close[:200])).to_numpy()
    assert (full[:200] == part).all()


def test_trend_flips_less_than_old_two_bar_rule():
    rng = np.random.default_rng(7)
    d = frame(100 * np.exp(np.cumsum(rng.normal(0, 0.03, 365))))
    s = d["SMA_25"]
    old = np.where((s > s.shift(1)) & (s.shift(1) > s.shift(2)), 1,
                   np.where((s < s.shift(1)) & (s.shift(1) < s.shift(2)), -1, 0))
    new = f.get_trend_val(d.copy()).to_numpy()
    flips = lambda x: int((np.diff(x) != 0).sum())
    assert flips(new) < flips(old)


def test_market_trend_uses_own_trends_and_real_caps():
    own = {"BTC": -1, "ETH": 1, "DOT": 0}
    eq, cap = f.market_trend(own, pd.Series({"BTC": 3.0, "ETH": 1.0, "DOT": 0.0}))
    assert eq == pytest.approx(0.0)
    assert cap == pytest.approx((-3 + 1) / 4)
    assert f.market_trend(own, None)[1] is None
    assert f.market_trend(own, pd.Series({"BTC": np.nan, "ETH": 1, "DOT": 1}))[1] is None


def test_drop_incomplete_daily_bar():
    d = pd.DataFrame({"close": [1.0, 2, 3]}, index=pd.to_datetime(["2026-10-17", "2026-10-18", "2026-10-19"]))
    out = f.drop_incomplete_daily_bar(d, now=pd.Timestamp("2026-10-19 12:30", tz="UTC"))
    assert list(out.index.strftime("%Y-%m-%d")) == ["2026-10-17", "2026-10-18"]


def test_market_caps_fallback_has_no_invented_numbers(monkeypatch):
    def boom(*a, **k):
        raise OSError("offline")
    monkeypatch.setattr(f.requests, "get", boom)
    f.get_market_caps.clear()
    df, src = f.get_market_caps()
    assert df["market_cap"].isna().all() and "unavailable" in src
    f.get_market_caps.clear()
