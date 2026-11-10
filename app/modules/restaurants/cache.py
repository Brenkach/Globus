"""Схема ключів і політика TTL для кешу модуля restaurants.

Шаблон ключа: globus:v1:<сутність>:<ідентифікатор>[:<параметри>]

  globus:v1:restaurant:{id}                         картка ресторану
  globus:v1:menu:restaurant:{id}:available:{0|1}    меню (тільки доступні / всі страви)
  globus:v1:nearby:gen:{n}:{hash}                   результат геопошуку; hash = sha1 нормалізованих параметрів

Кожен параметр, що впливає на відповідь, входить у ключ, тому різні відповіді
ніколи не потрапляють під один ключ (немає колізій).
"""

from __future__ import annotations

import hashlib

from app.core.cache import PREFIX

# TTL, секунди. Це «страховка» на випадок пропущеної інвалідації, а не основний механізм свіжості.
TTL_RESTAURANT = 600   # 10 хв: назва й адреса змінюються дуже рідко
TTL_MENU = 300         # 5 хв: ціни й наявність змінюються рідко, при зміні ключ скидається явно
TTL_NEARBY = 60        # 1 хв: точну інвалідацію неможливо, тому короткий TTL + покоління

NEARBY_GENERATION = "nearby"
# Округлення координат: 3 знаки ≈ 110 м. Клієнти в одному кварталі отримують спільний кеш.
COORD_PRECISION = 3


def restaurant_key(restaurant_id: int) -> str:
    return f"{PREFIX}:restaurant:{restaurant_id}"


def menu_key(restaurant_id: int, only_available: bool) -> str:
    return f"{PREFIX}:menu:restaurant:{restaurant_id}:available:{int(only_available)}"


def menu_keys(restaurant_id: int) -> list[str]:
    """Усі варіанти меню ресторану: скидаються разом при будь-якій зміні меню."""
    return [menu_key(restaurant_id, True), menu_key(restaurant_id, False)]


def normalize_point(lat: float, lng: float) -> tuple[float, float]:
    return round(lat, COORD_PRECISION), round(lng, COORD_PRECISION)


def nearby_key(gen: int, lat: float, lng: float, radius_m: float, limit: int) -> str:
    params = f"lat={lat:.{COORD_PRECISION}f}&lng={lng:.{COORD_PRECISION}f}&radius={radius_m:g}&limit={limit}"
    digest = hashlib.sha1(params.encode()).hexdigest()[:16]
    return f"{PREFIX}:nearby:gen:{gen}:{digest}"
