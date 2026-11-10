"""Експеримент 2.6: час відповіді холодного (Cache Miss) і гарячого (Cache Hit) запиту.

    python3 scripts/exp_cache_latency.py

Меню: N разів очистити кеш -> холодний запит -> гарячий запит.
Геопошук: N різних точок (кожна в своєму квадраті ~110 м): спершу всі холодні, потім ті самі гарячі.
Запити послідовні (по одному), щоб вимірювати саме затримку, а не чергу.
Результати: results/cache_latency.md
"""

from __future__ import annotations

import argparse
import math
import statistics
import time

from _lb import LB_URL, flush_cache, request_full, save_results

parser = argparse.ArgumentParser()
parser.add_argument("-n", type=int, default=30)
args = parser.parse_args()


def timed(url: str) -> tuple[float, str]:
    t = time.perf_counter()
    status, h, _ = request_full(url)
    if status != 200:
        raise SystemExit(f"HTTP {status} для {url}. Чи виконано seed?")
    return (time.perf_counter() - t) * 1000, h.get("x-cache", "?")


def pct(values: list[float], p: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, max(0, math.ceil(p / 100 * len(s)) - 1))]


def row(name: str, cold: list[float], hot: list[float]) -> str:
    c50, h50 = statistics.median(cold), statistics.median(hot)
    return (f"| {name} | {c50:.1f} | {pct(cold, 95):.1f} | {h50:.1f} | {pct(hot, 95):.1f} | "
            f"у {c50 / h50:.1f} раза |")


results = {}

print(f"Меню: {args.n} пар холодний / гарячий...")
cold, hot, bad = [], [], 0
for _ in range(args.n):
    flush_cache()
    ms, st = timed(f"{LB_URL}/restaurants/1/menu")
    cold.append(ms); bad += st != "MISS"
    ms, st = timed(f"{LB_URL}/restaurants/1/menu")
    hot.append(ms); bad += st != "HIT"
results["Меню ресторану `GET /restaurants/1/menu`"] = (cold, hot)
if bad:
    print(f"  увага: {bad} відповідей мали неочікуваний статус X-Cache")

print(f"Геопошук: {args.n} точок холодних, потім ті самі гарячі...")
flush_cache()
points = [(50.40 + i * 0.002, 30.52) for i in range(args.n)]
urls = [f"{LB_URL}/restaurants?lat={lat:.4f}&lng={lng:.4f}&radius_m=10000" for lat, lng in points]
cold = [timed(u)[0] for u in urls]
hot = [timed(u)[0] for u in urls]
results["Геопошук `GET /restaurants?lat=&lng=` (PostGIS)"] = (cold, hot)

lines = ["| Сценарій | MISS p50, мс | MISS p95, мс | HIT p50, мс | HIT p95, мс | Прискорення (p50) |",
         "|---|---|---|---|---|---|"]
lines += [row(name, c, h) for name, (c, h) in results.items()]
table = "\n".join(lines)
print("\n" + table)
path = save_results("cache_latency", f"Запити послідовні, через балансувальник, по {args.n} вимірювань.\n\n{table}\n")
print(f"\nЗбережено: {path}")
