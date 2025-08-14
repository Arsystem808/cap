# -*- coding: utf-8 -*-
from __future__ import annotations
import math
import numpy as np
import pandas as pd

# ---------- Pivot (Fibonacci) ----------
def fib_pivots(H: float, L: float, C: float) -> dict:
    P = (H + L + C) / 3.0
    R = (H - L)
    return {
        "P": P,
        "R1": P + 0.382 * R,
        "R2": P + 0.618 * R,
        "R3": P + 1.000 * R,
        "S1": P - 0.382 * R,
        "S2": P - 0.618 * R,
        "S3": P - 1.000 * R,
    }

def aggregate_prev_HLC(df: pd.DataFrame, horizon: str) -> tuple[float,float,float,str]:
    """
    ST -> strictly previous WEEK (weekly pivots)
    MID -> previous MONTH
    LT -> previous YEAR
    """
    if horizon == "ST":
        base_tf = "W"
        grp = df.resample("W").agg({"High":"max","Low":"min","Close":"last"}).dropna()
    elif horizon == "MID":
        base_tf = "M"
        grp = df.resample("M").agg({"High":"max","Low":"min","Close":"last"}).dropna()
    else:
        base_tf = "Y"
        grp = df.resample("Y").agg({"High":"max","Low":"min","Close":"last"}).dropna()

    if len(grp) < 2:
        if base_tf == "Y":
            grp = df.resample("M").agg({"High":"max","Low":"min","Close":"last"}).dropna()
        elif base_tf == "M":
            grp = df.resample("W").agg({"High":"max","Low":"min","Close":"last"}).dropna()
    row = grp.iloc[-2] if len(grp) >= 2 else df.iloc[-2]
    return float(row["High"]), float(row["Low"]), float(row["Close"]), base_tf

# ---------- Heikin Ashi ----------
def heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    ha = pd.DataFrame(index=df.index)
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    ha["HA_Close"] = (o + h + l + c) / 4.0
    ha["HA_Open"] = ha["HA_Close"].copy()
    for i in range(1, len(ha)):
        ha.iat[i, ha.columns.get_loc("HA_Open")] = (
            ha.iat[i-1, ha.columns.get_loc("HA_Open")] + ha.iat[i-1, ha.columns.get_loc("HA_Close")]
        ) / 2.0
    return ha

def streak_len(series: pd.Series, positive=True) -> int:
    s = series.dropna()
    cnt = 0
    for v in reversed(s.values):
        if v == 0: continue
        if (v > 0 and positive) or (v < 0 and not positive): cnt += 1
        else: break
    return cnt

# ---------- MACD histogram ----------
def macd_hist(close: pd.Series) -> pd.Series:
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd - signal

def hist_streak_and_flatness(hist: pd.Series) -> tuple[int, float]:
    s = hist.dropna()
    if s.empty: return 0, 0.0
    sign = 1 if s.iloc[-1] > 0 else (-1 if s.iloc[-1] < 0 else 0)
    k = 0
    for v in reversed(s.values):
        if v == 0: continue
        if (v > 0 and sign==1) or (v < 0 and sign==-1): k += 1
        else: break
    N = min(6, len(s))
    flat = s.diff().tail(N).abs().mean()
    return k, float(0 if math.isnan(flat) else flat)

# ---------- RSI ----------
def rsi_wilder(close: pd.Series, n=14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1/n, adjust=False).mean()
    roll_down = down.ewm(alpha=1/n, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    return rsi.fillna(50)

# ---------- ATR ----------
def atr(df: pd.DataFrame, period=14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# ---------- Helpers ----------
def near(x: float, lvl: float, rel_tol: float) -> bool:
    return abs(x - lvl) / max(1e-9, x) <= rel_tol

def targets_short(entry_zone: str, piv: dict) -> list[float]:
    # R3 -> [R2, P], R2 -> [max(P,S1), min(S1,S2)]
    if entry_zone == "R3":
        return [piv["R2"], piv["P"]]
    elif entry_zone == "R2":
        return [max(piv["P"], piv["S1"]), min(piv["S1"], piv["S2"])]
    return [max(piv["P"], piv["S1"]), piv["S2"]]

def targets_long(entry_zone: str, piv: dict) -> list[float]:
    # S3 -> [S2, P], S2 -> [min(P,R1), max(R1,R2)]
    if entry_zone == "S3":
        return [piv["S2"], piv["P"]]
    elif entry_zone == "S2":
        return [min(piv["P"], piv["R1"]), max(piv["R1"], piv["R2"])]
    return [min(piv["P"], piv["R1"]), piv["R2"]]

# ---------- Filters ----------
def regime_filter(df: pd.DataFrame, base_tf: str) -> str:
    # 'UP' | 'DOWN' | 'FLAT'  (на старшем ТФ)
    if base_tf == "W": res = df.resample("W").last()
    elif base_tf == "M": res = df.resample("M").last()
    else: res = df.resample("Y").last()
    close = res["Close"].dropna()
    if len(close) < 60: return "FLAT"
    ma = close.rolling(50).mean()
    slope = (ma.iloc[-1] - ma.iloc[-10]) / max(1e-9, ma.iloc[-10])
    vol = (close.rolling(14).std() / close).iloc[-1]
    if slope > 0.01 and vol < 0.06:
        return "UP"
    if slope < -0.01 and vol < 0.06:
        return "DOWN"
    return "FLAT"

def zone_confirmation(df: pd.DataFrame) -> bool:
    # простейший price-action: длинная тень против входа
    o, h, l, c = df["Open"].iloc[-1], df["High"].iloc[-1], df["Low"].iloc[-1], df["Close"].iloc[-1]
    rng = h - l
    if rng <= 0: return False
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    body = abs(c - o)
    bull = (lower_wick / max(1e-9, rng) >= 0.4) and (c > o) and (body/rng <= 0.6)
    bear = (upper_wick / max(1e-9, rng) >= 0.4) and (c < o) and (body/rng <= 0.6)
    return bull or bear

def rr_ok(entry: float, tp1: float, sl: float, min_rr: float = 2.0) -> bool:
    risk = abs(entry - sl)
    reward = abs(tp1 - entry)
    return (risk > 0) and (reward / risk >= min_rr)

def events_guard(date: pd.Timestamp, ticker: str) -> bool:
    # Заглушка: всегда True. (Подключим календарь позже)
    return True

# ---------- Overheat detector ----------
def detect_overheat(df: pd.DataFrame, piv: dict, horizon: str) -> dict:
    price = float(df["Close"].iloc[-1])
    ha = heikin_ashi(df)
    ha_streak = streak_len(ha["HA_Close"].diff(), positive=True)
    hist = macd_hist(df["Close"])
    hist_streak, flatness = hist_streak_and_flatness(hist)

    need_ha   = {"ST":4, "MID":5, "LT":6}[horizon]
    need_hist = {"ST":4, "MID":6, "LT":8}[horizon]
    tol       = {"ST":0.006, "MID":0.009, "LT":0.012}[horizon]

    at_res = any([near(price, piv["R2"], tol), near(price, piv["R3"], tol)]) or price >= piv["R2"]
    is_overheat = (ha_streak >= need_ha) and (hist_streak >= need_hist) and at_res

    pull_low = piv["S2"] if (price >= piv["R2"] and hist_streak >= need_hist+1) else piv["S1"]
    pull_high = max(piv["P"], piv["S1"])
    lo, hi = sorted([pull_low, pull_high])
    return {
        "overheat": bool(is_overheat),
        "ha_streak": int(ha_streak),
        "hist_streak": int(hist_streak),
        "at_res": bool(at_res),
        "pullback_zone": (round(lo,2), round(hi,2)),
        "flatness": round(float(flatness), 6),
    }

# ---------- Decision ----------
def decide(df: pd.DataFrame, horizon: str) -> dict:
    price = float(df["Close"].iloc[-1])
    H,L,C, base_tf = aggregate_prev_HLC(df, horizon)
    piv = fib_pivots(H,L,C)
    ctx = detect_overheat(df, piv, horizon)
    atr_last = float(atr(df).iloc[-1])

    atr_k_sl = {"ST":0.8, "MID":1.0, "LT":1.3}[horizon]

    def r(x):
        if x is None: return None
        try: return round(float(x), 2)
        except: return None

    at_top    = price >= piv["R2"]
    at_bottom = price <= piv["S2"]
    in_mid    = (piv["S1"] < price < piv["R1"])

    # базовые решения
    if horizon == "ST":
        if in_mid and not at_top and not at_bottom:
            base=("WAIT",None,None,None,None); alt=("WAIT",None,None,None,None)
        elif at_top and ctx["overheat"]:
            entry_zone = "R3" if price >= piv["R3"] else "R2"
            t1, t2 = targets_short(entry_zone, piv)
            entry = price
            sl = max(piv[entry_zone], entry) + atr_k_sl*atr_last
            base=("SHORT", entry, t1, t2, sl); alt=("WAIT",None,None,None,None)
        elif at_bottom:
            entry_zone = "S3" if price <= piv["S3"] else "S2"
            t1, t2 = targets_long(entry_zone, piv)
            entry = price
            sl = min(piv[entry_zone], entry) - atr_k_sl*atr_last
            base=("LONG", entry, t1, t2, sl); alt=("WAIT",None,None,None,None)
        else:
            base=("WAIT",None,None,None,None); alt=("WAIT",None,None,None,None)

    elif horizon == "MID":
        if ctx["overheat"] and at_top:
            base=("WAIT",None,None,None,None)
            entry_zone = "R3" if price >= piv["R3"] else "R2"
            t1, t2 = targets_short(entry_zone, piv)
            entry = max(piv["R2"], price)
            sl = max(piv[entry_zone], entry) + atr_k_sl*atr_last
            alt=("SHORT", entry, t1, t2, sl)
        elif at_bottom:
            entry_zone = "S3" if price <= piv["S3"] else "S2"
            t1, t2 = targets_long(entry_zone, piv)
            entry = min(piv["P"], price)
            sl = min(piv[entry_zone], entry) - atr_k_sl*atr_last
            base=("LONG", entry, t1, t2, sl); alt=("WAIT",None,None,None,None)
        else:
            base=("WAIT",None,None,None,None)
            alt =("LONG", min(piv["P"], price), piv["R1"], piv["R2"], min(piv["P"], price) - atr_k_sl*atr_last)

    else:  # LT
        if ctx["overheat"]:
            base=("WAIT",None,None,None,None)
            entry_zone = "R3" if price >= piv["R3"] else "R2"
            t1, t2 = targets_short(entry_zone, piv)
            entry = max(piv["R2"], price)
            sl = max(piv[entry_zone], entry) + atr_k_sl*atr_last
            alt=("SHORT", entry, t1, t2, sl)
        elif price <= piv["S2"]:
            entry_zone = "S3" if price <= piv["S3"] else "S2"
            t1, t2 = targets_long(entry_zone, piv)
            entry = min(piv["P"], price)
            sl = min(piv[entry_zone], entry) - atr_k_sl*atr_last
            base=("LONG", entry, t1, t2, sl); alt=("WAIT",None,None,None,None)
        else:
            base=("WAIT",None,None,None,None)
            alt =("LONG", min(piv["P"], price), piv["R1"], piv["R2"], min(piv["P"], price) - atr_k_sl*atr_last)

    # -------- общие фильтры --------
    base_tf_for_regime = {"ST":"W","MID":"M","LT":"Y"}[horizon]
    regime = regime_filter(df, base_tf_for_regime)

    def apply_filters(side):
        act, entry, tp1, tp2, sl = side
        if act in ("LONG","SHORT"):
            if not events_guard(df.index[-1], "TICKER"):
                return ("WAIT", None, None, None, None)
            if not zone_confirmation(df):
                return ("WAIT", None, None, None, None)
            if not rr_ok(entry, tp1, sl, 2.0):
                return ("WAIT", None, None, None, None)
            if act == "LONG" and regime == "DOWN":
                return ("WAIT", None, None, None, None)
            if act == "SHORT" and regime == "UP":
                return ("WAIT", None, None, None, None)
        return side

    base = apply_filters(base)
    alt  = apply_filters(alt)

    def r2(x):
        if x is None: return None
        try: return round(float(x), 2)
        except: return None

    out = {
        "price": round(price,2),
        "horizon": horizon,
        "pivots": {k: round(v,2) for k,v in piv.items()},
        "base": {"action": base[0], "entry": r2(base[1]), "tp1": r2(base[2]), "tp2": r2(base[3]), "sl": r2(base[4])},
        "alt":  {"action": alt[0],  "entry": r2(alt[1]),  "tp1": r2(alt[2]),  "tp2": r2(alt[3]),  "sl": r2(alt[4])},
        "ctx": {**ctx, "regime": regime}
    }
    return out
