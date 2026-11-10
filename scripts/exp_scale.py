"""Експеримент 2.5: scale-out 1 → 2 → 3 екземпляри.

Для кожної конфігурації зайві вузли зупиняються, HAProxy виключає їх з пулу
за health check, після чого запускається однакове навантаження.
Паралельно знімається завантаження CPU контейнерів, щоб побачити наступне вузьке місце.

    python3 scripts/exp_scale.py
    python3 scripts/exp_scale.py -c 60 --duration 30

Результати: results/scale.md
"""

from __future__ import annotations

import argparse
import threading
import time

from _lb import (SERVERS, SUMMARY_HEADER, docker_cpu_snapshot, run_load, save_results,
                 start, stop, summary_row, switch_algorithm, wait_pool)

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--concurrency", type=int, default=40)
parser.add_argument("--duration", type=float, default=20)
args = parser.parse_args()

switch_algorithm("leastconn")
rows, cpu_rows, base_rps = [], [], None

for n in (1, 2, 3):
    active, idle = SERVERS[:n], SERVERS[n:]
    print(f"\n=== {n} екземпляр(и): {', '.join(active)} ===")
    for name in active:
        start(name)
    for name in idle:
        stop(name)
    wait_pool(set(active))
    run_load(concurrency=args.concurrency, duration=3)  # прогрів

    snapshot = {}
    t = threading.Timer(args.duration / 2, lambda: snapshot.update(docker_cpu_snapshot()))
    t.start()
    r = run_load(concurrency=args.concurrency, duration=args.duration)
    t.join()

    base_rps = base_rps or r.rps
    row = summary_row(f"{n} instance(s)", r).rstrip(" |") + f" | x{r.rps / base_rps:.2f} |"
    rows.append(row)
    cpu = ", ".join(f"{k}: {v}" for k, v in sorted(snapshot.items())) or "немає даних docker stats"
    cpu_rows.append(f"| {n} | {cpu} |")
    print(row)
    print(f"CPU під навантаженням: {cpu}")

for name in SERVERS:
    start(name)
wait_pool(set(SERVERS))
switch_algorithm("roundrobin")

header = SUMMARY_HEADER.replace("| Розподіл по вузлах |", "| Розподіл по вузлах | Приріст RPS |")
header = header.replace("|---|---|---|---|---|---|---|---|", "|---|---|---|---|---|---|---|---|---|")
md = ["### Scale-out: 1 / 2 / 3 екземпляри (Least Connections)", "",
      f"Навантаження: {args.concurrency} клієнтів, {args.duration:.0f} с, кожен екземпляр обмежено 0.5 CPU.", "",
      header, *rows, "", "CPU контейнерів у середині прогону:", "", "| Екземплярів | CPU |", "|---|---|", *cpu_rows]
path = save_results("scale", "\n".join(md) + "\n")
print(f"\nЗбережено: {path}")
