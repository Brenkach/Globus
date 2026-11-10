"""Демонстрація для захисту ЛР4: Cache Hit / Miss та інвалідація (пункти 1–2 процедури захисту).

    python3 scripts/cache_demo.py

Крок за кроком: холодне читання меню (MISS) → повторні читання з різних екземплярів (HIT) →
зміна ціни через API → наступне читання (MISS, свіжа ціна) → знову HIT. Наприкінці ціна повертається.
"""

from __future__ import annotations

import json
import time

from _lb import LB_URL, flush_cache, request_full

MENU = f"{LB_URL}/restaurants/1/menu"


def read_menu(note: str) -> dict:
    t = time.perf_counter()
    status, h, body = request_full(MENU)
    ms = (time.perf_counter() - t) * 1000
    item = json.loads(body)[0]
    print(f"  GET menu  -> {h.get('x-cache', '?'):<6} instance={h.get('x-instance-id', '?'):<6} "
          f"{ms:6.1f} мс  ціна «{item['name']}»: {item['price']}   {note}")
    return item


print("0. Очищаю кеш, щоб почати з холодного стану")
flush_cache()

print("\n1. Cache Miss -> Cache Hit (кеш спільний для всіх екземплярів)")
item = read_menu("перший запит: даних у кеші немає, читаємо з БД")
for _ in range(3):
    read_menu("повтор: з Redis, без звернення до БД")

old_price = item["price"]
new_price = f"{float(old_price) + 1:.2f}"
print(f"\n2. Інвалідація: змінюю ціну страви {item['id']} {old_price} -> {new_price}")
status, h, _ = request_full(f"{LB_URL}/menu-items/{item['id']}", "PATCH",
                            json.dumps({"price": new_price}).encode())
print(f"  PATCH /menu-items/{item['id']} -> HTTP {status}, instance={h.get('x-instance-id')}  (ключ меню скинуто)")
read_menu("після зміни: MISS і свіжа ціна з БД")
read_menu("далі знову з кешу")

request_full(f"{LB_URL}/menu-items/{item['id']}", "PATCH", json.dumps({"price": old_price}).encode())
print(f"\nЦіну повернуто ({old_price}). Лічильники кешу:")
print(" ", request_full(f"{LB_URL}/cache/stats")[2].decode())
