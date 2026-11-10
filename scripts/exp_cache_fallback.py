"""Експеримент 2.6: відмова Redis під навантаженням (Graceful Degradation).

Безперервне навантаження на меню через балансувальник. На 8-й секунді Redis зупиняється,
на 18-й запускається. Посекундно видно джерело відповідей (HIT / MISS / BYPASS),
помилки клієнта і затримку.

    python3 scripts/exp_cache_fallback.py

Результати: results/cache_fallback.md
"""

from __future__ import annotations

import argparse
import statistics
import threading
from collections import Counter, defaultdict

from _lb import run_load, save_results, start, stop

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--concurrency", type=int, default=10)
parser.add_argument("--path", default="/restaurants/1/menu")
args = parser.parse_args()

DOWN_AT, UP_AT, DURATION = 8, 18, 32
events: dict[int, str] = {}


def on_tick(sec: int) -> None:
    if sec == DOWN_AT:
        events[sec] = "stop redis"
        threading.Thread(target=stop, args=("redis",)).start()
    elif sec == UP_AT:
        events[sec] = "start redis"
        threading.Thread(target=start, args=("redis",)).start()


print(f"Навантаження {DURATION} с на {args.path}; stop redis на {DOWN_AT}-й с, start на {UP_AT}-й с\n")
r = run_load(args.path, args.concurrency, DURATION, on_tick=on_tick)

per_sec: dict[int, Counter] = defaultdict(Counter)
lat: dict[int, list[float]] = defaultdict(list)
for s in r.samples:
    sec = int(s.t)
    if s.status >= 500 or s.status == 0:
        per_sec[sec]["ERR"] += 1
    else:
        per_sec[sec][s.cache or "?"] += 1
        lat[sec].append(s.latency * 1000)

lines = ["| Секунда | Подія | Запитів | HIT | MISS | BYPASS | Помилки | Затримка p50, мс |",
         "|---|---|---|---|---|---|---|---|"]
for sec in range(DURATION):
    c = per_sec[sec]
    p50 = f"{statistics.median(lat[sec]):.1f}" if lat[sec] else "-"
    lines.append(f"| {sec} | {events.get(sec, '')} | {sum(c.values())} | {c['HIT']} | {c['MISS']} | "
                 f"{c['BYPASS']} | {c['ERR']} | {p50} |")
table = "\n".join(lines)
print(table)


def phase(a: int, b: int) -> tuple[float, float]:
    n = sum(sum(per_sec[s].values()) for s in range(a, b))
    vals = [v for s in range(a, b) for v in lat[s]]
    return n / (b - a), (statistics.median(vals) if vals else 0.0)


rps_on, p50_on = phase(1, DOWN_AT)
rps_off, p50_off = phase(DOWN_AT + 2, UP_AT)
summary = (f"\nУсього запитів: {len(r.samples)}, помилок 5xx: {r.errors_5xx}, мережевих помилок: {r.errors_net}.\n"
           f"З кешем: ~{rps_on:.0f} запитів/с, p50 {p50_on:.1f} мс. "
           f"Без кешу (напряму з БД): ~{rps_off:.0f} запитів/с, p50 {p50_off:.1f} мс.")
print(summary)
ok = r.errors_5xx + r.errors_net == 0
print("РЕЗУЛЬТАТ:", "система працювала без Redis, помилок немає" if ok else "були помилки, див. таблицю")
path = save_results("cache_fallback", f"Навантаження: {args.concurrency} клієнтів, `{args.path}`.\n\n{table}\n{summary}\n")
print(f"Збережено: {path}")
