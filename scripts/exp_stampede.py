"""Захист від Cache Stampede (Thundering Herd).

Кеш порожній, і одночасно приходить N однакових запитів до дорогого геопошуку.
Без захисту всі N пішли б у БД. З розподіленим блокуванням (SET NX) у БД іде лише один,
решта чекають, поки він заповнить кеш, і отримують HIT.

    python3 scripts/exp_stampede.py -n 50

Результати: results/stampede.md
"""

from __future__ import annotations

import argparse
import json
import threading
from collections import Counter

from _lb import LB_URL, flush_cache, request_full, save_results

parser = argparse.ArgumentParser()
parser.add_argument("-n", type=int, default=50)
args = parser.parse_args()

url = f"{LB_URL}/restaurants?lat=50.4501&lng=30.5234&radius_m=20000&limit=50"
flush_cache()

barrier = threading.Barrier(args.n)
results: list[tuple[int, str, str]] = []
lock = threading.Lock()


def worker() -> None:
    barrier.wait()   # усі потоки стартують одночасно
    status, h, _ = request_full(url)
    with lock:
        results.append((status, h.get("x-cache", "?"), h.get("x-instance-id", "?")))


threads = [threading.Thread(target=worker) for _ in range(args.n)]
for t in threads:
    t.start()
for t in threads:
    t.join()

by_cache = Counter(c for _, c, _ in results)
by_inst = Counter(i for _, _, i in results)
errors = sum(1 for s, _, _ in results if s != 200)
text = (f"{args.n} одночасних запитів до холодного ключа геопошуку.\n\n"
        f"| Показник | Значення |\n|---|---|\n"
        f"| Пішли в БД (MISS) | {by_cache['MISS']} |\n"
        f"| Дочекались кешу (HIT) | {by_cache['HIT']} |\n"
        f"| Без кешу (BYPASS) | {by_cache['BYPASS']} |\n"
        f"| Помилки | {errors} |\n"
        f"| Розподіл по екземплярах | {', '.join(f'{k}: {v}' for k, v in sorted(by_inst.items()))} |\n")
print(text)
print("РЕЗУЛЬТАТ:", f"у БД пішов {by_cache['MISS']} запит(и) з {args.n}: запити з різних екземплярів "
      "дочекались одного заповнення кешу" if by_cache["MISS"] <= 1 else
      "у БД пішло кілька запитів (блокування не встигло, див. LOCK_WAIT_S)")
path = save_results("stampede", text)
print(f"Збережено: {path}")
