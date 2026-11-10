"""Навантажувальний тест через балансувальник: RPS, p50/p95/p99 і розподіл по Instance ID.

    python3 scripts/load_test.py                          # 20 клієнтів, 15 с, геопошук ресторанів
    python3 scripts/load_test.py -c 50 -d 30
    python3 scripts/load_test.py --path /health -c 5 -d 5
"""

from __future__ import annotations

import argparse

from _lb import DEFAULT_PATH, LB_URL, SUMMARY_HEADER, current_algorithm, run_load, summary_row

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--concurrency", type=int, default=20)
parser.add_argument("-d", "--duration", type=float, default=15)
parser.add_argument("--path", default=DEFAULT_PATH)
args = parser.parse_args()

print(f"{LB_URL}{args.path} | клієнтів: {args.concurrency} | {args.duration:.0f} с | алгоритм: {current_algorithm()}")
r = run_load(args.path, args.concurrency, args.duration)
print()
print(SUMMARY_HEADER)
print(summary_row(current_algorithm(), r))
