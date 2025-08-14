# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
from core_strategy import decide
from narrator import humanize
from backtest import run_backtest

st.set_page_config(page_title="CapinteL-Q AI (with filters)", page_icon="📈", layout="centered")
st.title("CapinteL-Q AI — живой анализ рынка (фильтры включены)")

@st.cache_data(ttl=900)
def load_yahoo(ticker: str, years: str) -> pd.DataFrame:
    df = yf.download(ticker, period=years, interval="1d", auto_adjust=False, progress=False)
    return df.rename(columns=str.title)[["Open","High","Low","Close"]].dropna()

# --- Input ---
col1, col2 = st.columns([2,1])
with col1:
    ticker = st.text_input("Тикер", value="QQQ").upper().strip()
with col2:
    horizon_label = st.selectbox("Горизонт",
        ["Авто", "Краткосрок (1–10 дн.)","Среднесрок (2–8 нед.)","Долгосрок (1–6 мес.)"])

period = st.selectbox("Период истории", ["1 год","3 года","5 лет"], index=1)

def map_hz(h):
    if h.startswith("Кратк"): return "ST"
    if h.startswith("Средн"): return "MID"
    if h.startswith("Долго"): return "LT"
    return None

years = {"1 год":"1y","3 года":"3y","5 лет":"5y"}[period]

st.divider()
tab1, tab2 = st.tabs(["Анализ", "Backtest"])

with tab1:
    if st.button("Проанализировать", type="primary"):
        try:
            with st.spinner("Загружаем данные и формируем взгляд..."):
                data = load_yahoo(ticker, years)
                if len(data) < 80:
                    st.error("Мало данных для анализа. Попробуйте увеличить период.")
                else:
                    hz = map_hz(horizon_label)
                    if hz is None:
                        rng = data["Close"].rolling(60).agg(["min","max"]).dropna()
                        if len(rng)==0:
                            hz = "MID"
                        else:
                            pos = (data["Close"].iloc[-1] - rng["min"].iloc[-1]) / max(1e-9, (rng["max"].iloc[-1]-rng["min"].iloc[-1]))
                            hz = "LT" if pos > 0.85 or pos < 0.15 else ("MID" if 0.25 < pos < 0.75 else "ST")
                    res = decide(data, hz)
                    txt = humanize(ticker, hz, res)
                    st.markdown(txt)
        except Exception as e:
            st.error(f"Ошибка анализа: {e}")

with tab2:
    st.subheader("Исторический прогон (до 5 лет)")
    colb1, colb2, colb3 = st.columns(3)
    with colb1:
        bt_hz_label = st.selectbox("Горизонт (бэктест)", 
            ["Краткосрок (1–10 дн.)","Среднесрок (2–8 нед.)","Долгосрок (1–6 мес.)"])
    with colb2:
        capital = st.number_input("Стартовый капитал, $", 10000, 10000000, 100000, step=10000)
    with colb3:
        risk = st.slider("Риск на сделку", 0.2, 5.0, 1.0, step=0.2) / 100.0

    if st.button("Запустить Backtest"):
        try:
            with st.spinner("Грузим данные и считаем сделки..."):
                data = load_yahoo(ticker, years)
                hz = map_hz(bt_hz_label)
                eq, tr = run_backtest(data, hz, capital, risk)
                if eq is None or eq.empty:
                    st.info("Нет сделок по заданным условиям.")
                else:
                    st.line_chart(eq, y="equity")
                    st.write(f"Сделки: {len(tr)}")
                    if not tr.empty:
                        st.dataframe(tr)

                        # --- метрики бэктеста ---
                        if "tp1_hit" in tr.columns:
                            tr["tp1_hit"] = tr["tp1_hit"].fillna(False)
                            wins = int(tr["tp1_hit"].sum())
                        else:
                            wins = 0
                        total = len(tr)
                        hit_rate = 100.0 * wins / max(1, total)

                        total_pnl = float(tr.get("pnl", pd.Series([0]*total)).sum())
                        roll_max = eq["equity"].cummax()
                        drawdown = (eq["equity"] - roll_max) / roll_max
                        max_dd = 100.0 * float(drawdown.min())

                        st.markdown(
                            f"**Hit-rate (TP1 до SL):** {hit_rate:.1f}%  \n"
                            f"**Сделок:** {total}  \n"
                            f"**Итоговый P/L:** ${total_pnl:,.0f}  \n"
                            f"**Макс. просадка:** {max_dd:.1f}%"
                        )
        except Exception as e:
            st.error(f"Ошибка бэктеста: {e}")

st.caption("⚠️ Результаты — не инвестиционный совет. Продукт демонстрационный, логика скрыта от клиента.")
