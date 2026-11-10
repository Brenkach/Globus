"""Експеримент 2.4: відмова вузла під навантаженням і автоматичне відновлення пулу.

Через балансувальник іде безперервне навантаження. На 5-й секунді app2 зупиняється
(або вбивається, з --kill), на 15-й запускається знову. Скрипт показує посекундно,
які вузли обслуговують трафік, і скільки помилок 5xx отримав клієнт.

    python3 scripts/exp_failover.py
    python3 scripts/exp_failover.py --kill        # аварійно (SIGKILL), а не штатно

Результати: results/failover.md
"""

from __future__ import annotations

import argparse
import threading
from collections import Counter, defaultdict

from _lb import (SERVERS, kill, pool_status, run_load, save_results, start, stop, wait_pool)

parser = argparse.ArgumentParser()
parser.add_argument("--kill", action="store_true", help="docker compose kill замість stop")
parser.add_argument("--victim", default="app2")
parser.add_argument("-c", "--concurrency", type=int, default=10)
parser.add_argument("--path", default="/restaurants/1/menu")
args = parser.parse_args()

DOWN_AT, UP_AT, DURATION = 5, 15, 30
events: dict[int, str] = {}
pool_log: dict[int, str] = {}

wait_pool(set(SERVERS))
mode = "kill" if args.kill else "stop"
print(f"Навантаження {DURATION} с; {mode} {args.victim} на {DOWN_AT}-й с, start на {UP_AT}-й с\n")


def on_tick(sec: int) -> None:
    try:
        st = pool_status()
        pool_log[sec] = " ".join(f"{k}={v.split()[0]}" for k, v in sorted(st.items()))
    except Exception:
        pool_log[sec] = "?"
    if sec == DOWN_AT:
        events[sec] = f"{mode} {args.victim}"
        threading.Thread(target=(kill if args.kill else stop), args=(args.victim,)).start()
    elif sec == UP_AT:
        events[sec] = f"start {args.victim}"
        threading.Thread(target=start, args=(args.victim,)).start()


r = run_load(args.path, args.concurrency, DURATION, on_tick=on_tick)

per_sec: dict[int, Counter] = defaultdict(Counter)
errors: Counter = Counter()
for s in r.samples:
    sec = int(s.t)
    if s.status >= 500 or s.status == 0:
        errors[sec] += 1
    else:
        per_sec[sec][s.instance] += 1

lines = ["| Секунда | Подія | Обслужили (app-1 / app-2 / app-3) | Помилки клієнта | Стан пулу в HAProxy |",
         "|---|---|---|---|---|"]
for sec in range(DURATION):
    c = per_sec[sec]
    served = f"{c['app-1']} / {c['app-2']} / {c['app-3']}"
    lines.append(f"| {sec} | {events.get(sec, '')} | {served} | {errors[sec]} | {pool_log.get(sec + 1, '')} |")
table = "\n".join(lines)
print(table)

total_err = r.errors_5xx + r.errors_net
summary = (f"\nУсього запитів: {len(r.samples)}, успішних: {len(r.ok)}, "
           f"помилок 5xx: {r.errors_5xx}, мережевих помилок: {r.errors_net}.")
print(summary)
print("РЕЗУЛЬТАТ:", "відмова вузла пройшла непомітно для клієнта" if total_err == 0
      else "були помилки, див. таблицю")

path = save_results(f"failover_{mode}", f"### Відмова вузла ({mode} {args.victim})\n\n{table}\n{summary}\n")
print(f"Збережено: {path}")
