"""Експеримент 2.3: порівняння алгоритмів балансування.

Частина A: розподіл запитів для Round Robin, Weighted RR (3:1:1), IP Hash, Least Connections.
Частина B: асиметричне навантаження. На app2 вмикається затримка (за замовчуванням 300 мс),
і порівнюються Round Robin та Least Connections за RPS і p99.

    python3 scripts/exp_algorithms.py
    python3 scripts/exp_algorithms.py --delay 500 --duration 30

Результати друкуються і зберігаються в results/algorithms.md
"""

from __future__ import annotations

import argparse

from _lb import (ALGORITHMS, SERVERS, SUMMARY_HEADER, run_load, save_results, set_delay,
                 summary_row, switch_algorithm, wait_pool)

parser = argparse.ArgumentParser()
parser.add_argument("--delay", type=int, default=300, help="затримка app2, мс")
parser.add_argument("--duration", type=float, default=20)
parser.add_argument("-c", "--concurrency", type=int, default=30)
args = parser.parse_args()

out = []
all_up = set(SERVERS)


def measure(algo: str):
    """Перемкнути алгоритм, прогріти 3 с (не враховується), потім виміряти."""
    switch_algorithm(algo)
    run_load(concurrency=args.concurrency, duration=3)
    return run_load(concurrency=args.concurrency, duration=args.duration)


print("Готую пул: усі вузли без затримки...")
set_delay("app2", 0)
wait_pool(all_up)

print("\n=== A. Розподіл запитів (рівноправні вузли) ===")
out += ["### A. Розподіл запитів при рівноправних вузлах", "",
        f"Навантаження: {args.concurrency} клієнтів, {args.duration:.0f} с на кожен алгоритм.", "", SUMMARY_HEADER]
for algo in ["roundrobin", "weighted", "source", "leastconn"]:
    r = measure(algo)
    row = summary_row(f"{algo} ({ALGORITHMS[algo].split(':')[0]})", r)
    print(row)
    out.append(row)

print(f"\n=== B. Асиметричне навантаження: app2 повільніший на {args.delay} мс ===")
set_delay("app2", args.delay)
wait_pool(all_up)
out += ["", f"### B. Асиметричне навантаження: app2 з затримкою {args.delay} мс", "", SUMMARY_HEADER]
results = {}
for algo in ["roundrobin", "leastconn"]:
    r = measure(algo)
    results[algo] = r
    row = summary_row(algo, r)
    print(row)
    out.append(row)

rr, lc = results["roundrobin"], results["leastconn"]
conclusion = (
    f"\nLeast Connections проти Round Robin: RPS {lc.rps:.1f} проти {rr.rps:.1f} "
    f"({(lc.rps / rr.rps - 1) * 100 if rr.rps else 0:+.0f}%), "
    f"p99 {lc.percentile(99):.0f} мс проти {rr.percentile(99):.0f} мс. "
    f"Частка запитів на повільний app2: {lc.distribution()['app-2'] * 100 / max(1, len(lc.ok)):.0f}% "
    f"проти {rr.distribution()['app-2'] * 100 / max(1, len(rr.ok)):.0f}%."
)
print(conclusion)
out.append(conclusion)

print("\nПовертаю пул у вихідний стан (без затримки, roundrobin)...")
set_delay("app2", 0)
switch_algorithm("roundrobin")
path = save_results("algorithms", "\n".join(out) + "\n")
print(f"Збережено: {path}")
