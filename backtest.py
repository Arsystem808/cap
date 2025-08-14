# -*- coding: utf-8 -*-
from __future__ import annotations
import pandas as pd
from core_strategy import decide

def run_backtest(df: pd.DataFrame, horizon: str, initial_capital=100000, risk_per_trade=0.01):
    cap = initial_capital
    pos = None
    trades = []
    equity = []

    for i in range(60, len(df)):
        sub = df.iloc[:i].copy()
        dec = decide(sub, horizon)
        price = sub["Close"].iloc[-1]
        date  = sub.index[-1].date()

        # управление активной позицией
        if pos:
            high = sub["High"].iloc[-1]
            low  = sub["Low"].iloc[-1]
            closed = False

            if pos["side"] == "LONG":
                if low <= pos["sl"]:
                    pnl = (pos["sl"] - pos["entry"]) * pos["size"]
                    cap += pnl
                    pos["exit"], pos["pnl"], pos["exit_date"] = pos["sl"], pnl, date
                    trades.append(pos); pos=None; closed=True
                if not closed:
                    if high >= pos["tp1"] and not pos.get("tp1_hit"):
                        pnl = (pos["tp1"] - pos["entry"]) * pos["size"]*0.5
                        cap += pnl; pos["tp1_hit"]=True
                    if high >= pos["tp2"]:
                        pnl = (pos["tp2"] - pos["entry"]) * pos["size"]*0.5
                        cap += pnl
                        pos["exit"], pos["pnl"], pos["exit_date"] = pos["tp2"], pnl + (pos["tp1"]-pos["entry"]) * pos["size"]*0.5, date
                        trades.append(pos); pos=None

            else:  # SHORT
                if high >= pos["sl"]:
                    pnl = (pos["entry"] - pos["sl"]) * pos["size"]
                    cap += pnl
                    pos["exit"], pos["pnl"], pos["exit_date"] = pos["sl"], pnl, date
                    trades.append(pos); pos=None; closed=True
                if not closed:
                    if low <= pos["tp1"] and not pos.get("tp1_hit"):
                        pnl = (pos["entry"] - pos["tp1"]) * pos["size"]*0.5
                        cap += pnl; pos["tp1_hit"]=True
                    if low <= pos["tp2"]:
                        pnl = (pos["entry"] - pos["tp2"]) * pos["size"]*0.5
                        cap += pnl
                        pos["exit"], pos["pnl"], pos["exit_date"] = pos["tp2"], pnl + (pos["entry"]-pos["tp1"]) * pos["size"]*0.5, date
                        trades.append(pos); pos=None

        # открытие новой позиции
        if (pos is None) and (dec["base"]["action"] in ["LONG","SHORT"]):
            entry, tp1, tp2, sl = dec["base"]["entry"], dec["base"]["tp1"], dec["base"]["tp2"], dec["base"]["sl"]
            if None not in [entry,tp1,tp2,sl]:
                risk_amt = cap * risk_per_trade
                risk_per_share = abs(entry - sl)
                if risk_per_share > 0:
                    size = max(1, int(risk_amt / risk_per_share))
                    pos = {
                        "side": dec["base"]["action"],
                        "entry": entry, "tp1": tp1, "tp2": tp2, "sl": sl,
                        "size": size, "entry_date": date, "comment": ""
                    }

        equity.append({"date": date, "equity": cap})

    eq = pd.DataFrame(equity).set_index("date")
    tr = pd.DataFrame(trades)
    return eq, tr

        
