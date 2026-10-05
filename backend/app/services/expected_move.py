"""Expected-move check (a light version of the design handoff's model).

Per holding, daily:  expected = a + b * r_index,  residual = actual - expected,
z = residual / stdev(in-sample residuals).

Index only: on daily data the handoff's macro factors add little beyond the index for single
names and make the fit less stable, so they're left to the Macro screen. The flag bar is
|z| >= 2.5 rather than 2 so a 12-name book isn't flagging noise most days. A move on a
results day (the earnings date, or the session after it for after-close reports) is labelled
"earnings", not "unexplained". An unexplained move on a holding without an analysis is the
prompt to run one.

OLS over the last 250 trading days before the day being explained; below 60, no model.
Computed on request from Yahoo history and cached for the day.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import numpy as np

from app.services.index_map import INDEX_YAHOO

LOOKBACK = 250
MIN_HISTORY = 60
FLAG_Z = 2.5
# (name, yahoo, "ret" | "diff", label). Empty by design; see the module docstring.
FACTORS: list[tuple[str, str, str, str]] = []
DEFAULT_INDEX = "SPX"

_cache: dict[tuple, dict] = {}
_lock = threading.Lock()


def _download(symbols: list[str]):
    import yfinance as yf
    df = yf.download(sorted(set(symbols)), period="2y", interval="1d", auto_adjust=True, progress=False)["Close"]
    return df


def _earnings_days(symbol: str) -> set[str]:
    try:
        import yfinance as yf
        ed = yf.Ticker(symbol).earnings_dates
        return {ts.date().isoformat() for ts in (ed.index if ed is not None else [])}
    except Exception:
        return set()


def fit_and_explain(stock, index, factors: dict, dates: list[str], earnings: set[str]) -> dict | None:
    """Pure model step on aligned arrays (closes / levels, same length as dates). Returns the
    explanation of the last day, or None when there isn't MIN_HISTORY of usable data."""
    stock, index = np.asarray(stock, float), np.asarray(index, float)
    y = stock[1:] / stock[:-1] - 1
    cols = [index[1:] / index[:-1] - 1]
    names = ["index"]
    for name, (kind, series) in factors.items():
        s = np.asarray(series, float)
        cols.append(s[1:] - s[:-1] if kind == "diff" else s[1:] / s[:-1] - 1)
        names.append(name)
    X = np.column_stack(cols)
    ok = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    y, X, d = y[ok], X[ok], [dt for dt, keep in zip(dates[1:], ok) if keep]
    if len(y) < MIN_HISTORY + 1:
        return None

    train = slice(max(0, len(y) - 1 - LOOKBACK), len(y) - 1)
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A[train], y[train], rcond=None)
    fitted = A[train] @ beta
    resid = y[train] - fitted
    sigma = float(np.std(resid, ddof=len(beta)))
    ss_tot = float(np.sum((y[train] - y[train].mean()) ** 2))
    r2 = 1 - float(np.sum(resid ** 2)) / ss_tot if ss_tot else 0.0

    today = A[-1]
    expected = float(today @ beta)
    actual = float(y[-1])
    residual = actual - expected
    z = residual / sigma if sigma else 0.0
    day = d[-1]
    prev = d[-2] if len(d) > 1 else None
    on_results = day in earnings or (prev in earnings if prev else False)
    category = "none" if abs(z) < FLAG_Z else ("earnings" if on_results else "unexplained")
    contrib = {n: float(today[i + 1] * beta[i + 1]) for i, n in enumerate(names)}
    contrib["alpha"] = float(beta[0])
    return {
        "date": day, "actual_pct": actual * 100, "expected_pct": expected * 100,
        "residual_pct": residual * 100, "z": z, "category": category,
        "attribution_pct": {k: v * 100 for k, v in contrib.items()},
        "betas": {n: float(beta[i + 1]) for i, n in enumerate(names)},
        "r2": r2, "n": int(train.stop - train.start), "sigma_pct": sigma * 100,
        "fit_from": d[train.start], "fit_to": d[train.stop - 1],
    }


def explain_holdings(holdings: list[dict], today: date | None = None) -> dict:
    """holdings: [{"ticker", "yahoo", "index"}]. Returns {ticker: explanation | None}."""
    key = ((today or date.today()).isoformat(), tuple(sorted((h["ticker"], h["yahoo"] or "", h["index"] or "") for h in holdings)))
    with _lock:
        if key in _cache:
            return _cache[key]

    index_syms = {h["index"] or DEFAULT_INDEX for h in holdings}
    symbols = [h["yahoo"] for h in holdings if h["yahoo"]] + [INDEX_YAHOO[c] for c in index_syms if c in INDEX_YAHOO] + [f[1] for f in FACTORS]
    try:
        df = _download(symbols)
    except Exception:
        return {h["ticker"]: None for h in holdings}

    with ThreadPoolExecutor(max_workers=8) as pool:
        held_syms = [h["yahoo"] for h in holdings if h["yahoo"]]
        earnings = dict(zip(held_syms, pool.map(_earnings_days, held_syms)))

    out = {}
    for h in holdings:
        sym = h["yahoo"]
        idx = INDEX_YAHOO.get(h["index"] or DEFAULT_INDEX, INDEX_YAHOO[DEFAULT_INDEX])
        if not sym or sym not in df:
            out[h["ticker"]] = None
            continue
        cols = [sym, idx] + [f[1] for f in FACTORS]
        # Factors / index carried forward over the stock's trading days (London vs US holidays).
        frame = df[cols].ffill().dropna(subset=[sym])
        frame = frame[frame[sym].notna()].dropna()
        dates = [ts.date().isoformat() for ts in frame.index]
        factors = {name: (kind, frame[s].to_numpy()) for name, s, kind, _ in FACTORS}
        try:
            out[h["ticker"]] = fit_and_explain(frame[sym].to_numpy(), frame[idx].to_numpy(), factors, dates, earnings.get(sym, set()))
        except Exception:
            out[h["ticker"]] = None
        if out[h["ticker"]]:
            out[h["ticker"]]["index_code"] = h["index"] or DEFAULT_INDEX

    with _lock:
        _cache.clear()
        _cache[key] = out
    return out


FACTOR_LABELS = {"index": "index", **{name: label for name, _, _, label in FACTORS}, "alpha": "drift"}
