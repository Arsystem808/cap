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
    regime = decision.get("ctx",{}).get("regime","?")

    intros = {
        "ST": [
            "Сейчас важнее точность, чем скорость.",
            "От краёв беру охотнее, серединку пропускаю.",
            "Если рынок тянет без отдыха — часто возвращается быстро."
        ],
        "MID": [
            "Рынок проверяет силу — не спешим.",
            "Дождусь перезагрузки в опорной зоне — там преимущество.",
            "Лишняя активность сейчас хуже, чем ожидание."
        ],
        "LT": [
            "Под потолком не покупаю — встречу ниже.",
            "Здесь важнее качество точки, чем ранний вход.",
            "Пусть рынок выдохнет — там будет наша зона."
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

    headline = f"📈 {ticker} — {hz} (режим: {regime})\nТекущая цена: {price}\n\n{intro}\n"
    body = block("✅ План", base) + "\n" + block("🔁 Альтернатива", alt)

    tails = [
        "Если сценарий подтверждается — работаем; ломается — выходим без колебаний.",
        "Не бегаем за ценой. Берём там, где перевес на нашей стороне.",
        "План есть — наблюдаем и действуем по факту."
    ]
    tail = pick(tails, seed_key=hz+ticker)
    return f"{headline}\n{body}\n\n{tail}"

