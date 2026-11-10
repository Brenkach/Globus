"""Розподілений кеш (Redis) і паттерн Cache-Aside (Lazy Loading).

Алгоритм cache_aside(key, ttl, loader):
  1. Key Lookup: GET key у Redis.
  2. Cache Hit: повертаємо об'єкт з кешу, БД не чіпаємо.
  3. Cache Miss: loader() читає з БД, результат записується в Redis з TTL і повертається.

Додатково:
  * Захист від Cache Stampede: при промаху лише ОДИН запит (з усіх екземплярів) іде в БД,
    решта коротко чекає, поки він заповнить кеш (розподілене блокування SET NX).
  * TTL з розкидом ±10% проти Cache Avalanche (одночасного закінчення терміну багатьох ключів).
  * Fallback: будь-яка помилка Redis означає роботу напряму з БД (Graceful Degradation).
    Статус BYPASS у заголовку X-Cache.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger("globus.cache")

PREFIX = "globus:v1"          # версія схеми ключів: змінити, якщо змінюється формат даних у кеші
STATS_KEY = f"{PREFIX}:stats"  # спільні лічильники hit / miss / bypass / invalidation

HIT, MISS, BYPASS = "HIT", "MISS", "BYPASS"

LOCK_TTL_MS = 3000             # скільки живе блокування заповнення, якщо власник упав
LOCK_WAIT_S = 1.0              # скільки інші запити чекають заповнення кешу
LOCK_POLL_S = 0.05

redis_client: Redis = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_timeout=settings.cache_timeout_s,
    socket_connect_timeout=settings.cache_timeout_s,
)

# Circuit breaker. Це локальний стан процесу, але не бізнес-стан: він лише вирішує,
# чи варто цьому екземпляру зараз пробувати Redis. Втрата цього значення нічого не ламає.
# Одиночна помилка (випадковий таймаут) пускає в обхід кешу лише один запит;
# після FAILURES_TO_TRIP помилок поспіль кеш вимикається на cache_retry_after_s секунд,
# щоб не витрачати таймаут на кожен запит, поки Redis лежить.
FAILURES_TO_TRIP = 3
_skip_until = 0.0
_failures = 0


def _available() -> bool:
    return settings.cache_enabled and time.monotonic() >= _skip_until


def _ok() -> None:
    global _failures
    _failures = 0


def _trip(exc: Exception) -> None:
    global _skip_until, _failures
    _failures += 1
    if _failures >= FAILURES_TO_TRIP:
        _skip_until = time.monotonic() + settings.cache_retry_after_s
        _failures = 0
        logger.warning("Redis unavailable (%s), cache bypassed for %.0fs", type(exc).__name__,
                       settings.cache_retry_after_s)
    else:
        logger.info("Redis error (%s), request served from DB", type(exc).__name__)


def jittered(ttl: int) -> int:
    """TTL з розкидом ±10%: ключі, створені одночасно, не закінчуються одночасно."""
    return max(1, int(ttl * random.uniform(0.9, 1.1)))


async def _count(field: str, n: int = 1) -> None:
    try:
        await redis_client.hincrby(STATS_KEY, field, n)
    except RedisError:
        pass


async def cache_aside(key: str, ttl: int, loader: Callable[[], Awaitable[Any]]) -> tuple[Any, str]:
    """Повертає (дані, статус), де статус: HIT, MISS або BYPASS."""
    if not _available():
        return await loader(), BYPASS

    try:
        cached = await redis_client.get(key)
        _ok()
        if cached is not None:
            await _count("hit")
            logger.info("cache HIT %s", key)
            return json.loads(cached), HIT

        # Промах. Пробуємо стати тим єдиним, хто піде в БД.
        lock_key = f"{key}:lock"
        got_lock = await redis_client.set(lock_key, "1", nx=True, px=LOCK_TTL_MS)
        if got_lock:
            # Double-checked locking: поки ми брали блокування, попередній власник
            # міг уже заповнити кеш і зняти своє блокування. Тоді в БД іти не треба.
            cached = await redis_client.get(key)
            if cached is not None:
                await redis_client.delete(lock_key)
                await _count("hit")
                return json.loads(cached), HIT
        else:
            # Хтось інший (можливо, інший екземпляр) уже заповнює кеш: чекаємо результат.
            deadline = time.monotonic() + LOCK_WAIT_S
            while time.monotonic() < deadline:
                await asyncio.sleep(LOCK_POLL_S)
                cached = await redis_client.get(key)
                if cached is not None:
                    await _count("hit")
                    return json.loads(cached), HIT
            # Не дочекались: краще самим сходити в БД, ніж віддати помилку.
    except RedisError as exc:
        _trip(exc)
        await _count("bypass")
        return await loader(), BYPASS

    try:
        data = await loader()   # винятки бізнес-логіки (404 тощо) не кешуються і летять далі
    except Exception:
        if got_lock:
            try:
                await redis_client.delete(lock_key)
            except RedisError:
                pass
        raise
    try:
        await redis_client.set(key, json.dumps(data, ensure_ascii=False), ex=jittered(ttl))
        if got_lock:
            await redis_client.delete(lock_key)
        await _count("miss")
        logger.info("cache MISS %s (ttl %ss)", key, ttl)
        return data, MISS
    except RedisError as exc:
        _trip(exc)
        return data, BYPASS


async def invalidate(*keys: str) -> None:
    """Явне скидання ключів після зміни даних. Помилка Redis не зриває операцію запису."""
    if not keys or not settings.cache_enabled:
        return
    try:
        removed = await redis_client.delete(*keys)
        await _count("invalidation", len(keys))
        logger.info("cache INVALIDATE %s (removed %s)", ", ".join(keys), removed)
    except RedisError as exc:
        _trip(exc)
        logger.error("cache invalidation FAILED for %s: stale data possible until TTL", keys)


async def bump_generation(name: str) -> None:
    """Інвалідація групи ключів, які неможливо перелічити (напр., усі результати геопошуку):
    збільшуємо номер покоління, і старі ключі просто перестають використовуватися."""
    if not settings.cache_enabled:
        return
    try:
        gen = await redis_client.incr(f"{PREFIX}:gen:{name}")
        await _count("invalidation")
        logger.info("cache INVALIDATE generation %s -> %s", name, gen)
    except RedisError as exc:
        _trip(exc)


async def generation(name: str) -> int | None:
    """Поточне покоління групи; None, якщо Redis недоступний."""
    if not _available():
        return None
    try:
        return int(await redis_client.get(f"{PREFIX}:gen:{name}") or 0)
    except RedisError as exc:
        _trip(exc)
        return None


async def stats() -> dict:
    try:
        raw = await redis_client.hgetall(STATS_KEY)
        info = await redis_client.info("memory")
        hits, misses = int(raw.get("hit", 0)), int(raw.get("miss", 0))
        return {
            "status": "ok",
            "hit": hits,
            "miss": misses,
            "bypass": int(raw.get("bypass", 0)),
            "invalidation": int(raw.get("invalidation", 0)),
            "hit_ratio": round(hits / (hits + misses), 3) if hits + misses else None,
            "used_memory": info.get("used_memory_human"),
            "maxmemory_policy": info.get("maxmemory_policy"),
        }
    except RedisError:
        return {"status": "unavailable"}


async def ping() -> bool:
    try:
        return bool(await redis_client.ping())
    except RedisError:
        return False
