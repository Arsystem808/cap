# -*- coding: utf-8 -*-
from __future__ import annotations
import random

def pick(arr, seed_key=""):
    random.seed(str(seed_key))
    return random.choice(arr)

def humanize(ticker: str, horizon: str, decision: dict) -> str:
    hz = {"ST":"краткосрок","MID":"среднесрок","LT":"долгосрок"}[horizon]
    price = decision["price"]
    base, alt = decision["base"], decision["alt"]

    intros = {
        "ST": [
            "В такие моменты беру только от края и без суеты.",
            "Сейчас важнее точность, чем скорость.",
            "Если рынок тянет без отдыха, часто заканчивается резким возвратом."
        ],
        "MID": [
            "Рынок перешёл в фазу проверки силы — не спешим.",
            "Предпочту дождаться перезагрузки у опорной зоны.",
            "Сейчас выигрывает терпение и дисциплина."
        ],
        "LT": [
            "Под потолком не покупаю — жду, где перевес на нашей стороне.",
            "Пусть рынок выдохнет — встречу его ниже, в выгодном коридоре.",
            "Здесь важнее качество точки, чем ранний вход."
        ]
    }
    intro = pick(intros[horizon], seed_key=ticker+hz+str(price))

    def block(title, side):
        act = side["action"]
        if act == "WAIT":
            return f"{title}:\n→ WAIT\n"
        txt = [f"{title}: {act}"]
        if side["entry"] is not None: txt.append(f"вход: {side['entry']}")
        if side["tp1"] is not None:   txt.append(f"цель 1: {side['tp1']}")
        if side["tp2"] is not None:   txt.append(f"цель 2: {side['tp2']}")
        if side["sl"]  is not None:   txt.append(f"защита: {side['sl']}")
        return " | ".join(txt)

    headline = f"📈 {ticker} — {hz}\nТекущая цена: {price}\n\n{intro}\n"
    body = block("✅ План", base) + "\n" + block("🔁 Альтернатива", alt)

    tails = [
        "Если сценарий подтвердится — работаем; если ломается — выходим без колебаний.",
        "Не спешим: рынок даст точку — наша задача её дождаться.",
        "План есть, теперь наблюдаем и действуем по факту."
    ]
    tail = pick(tails, seed_key=hz+ticker)
    return f"{headline}\n{body}\n\n{tail}"
