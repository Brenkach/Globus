"""Спільні функції для експериментів ЛР3 (лише стандартна бібліотека Python 3.9+).

Працює однаково на macOS, Linux і Windows. Усі запити йдуть ТІЛЬКИ через балансувальник.
"""

from __future__ import annotations

import csv
import io
import math
import os
import re
import shlex
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
LB_URL = os.environ.get("LB_URL", "http://localhost:8000")
STATS_URL = os.environ.get("STATS_URL", "http://localhost:8404/;csv")
LB_CONFIG = Path(os.environ.get("LB_CONFIG", str(ROOT / "haproxy" / "haproxy.cfg")))
BACKEND = "globus_api"
SERVERS = ["app1", "app2", "app3"]
DEFAULT_PATH = "/restaurants?lat=50.445&lng=30.52"

# Команди керування середовищем. Можна перевизначити змінними оточення (напр. для запуску без Docker).
RELOAD_CMD = os.environ.get("LB_RELOAD_CMD", "docker compose kill -s HUP lb")
STOP_CMD = os.environ.get("STOP_CMD", "docker compose stop {name}")
KILL_CMD = os.environ.get("KILL_CMD", "docker compose kill {name}")
START_CMD = os.environ.get("START_CMD", "docker compose start {name}")
# Перестворити екземпляр із затримкою: змінна APPn_DELAY_MS підставляється в docker-compose.yml.
DELAY_CMD = os.environ.get("DELAY_CMD", "docker compose up -d --no-deps {name}")


# ---------------------------------------------------------------- керування середовищем

def run(cmd: str, extra_env: dict | None = None, check: bool = True) -> str:
    env = dict(os.environ, **(extra_env or {}))
    res = subprocess.run(shlex.split(cmd), cwd=ROOT, env=env, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Команда завершилась з помилкою: {cmd}\n{res.stderr.strip()}")
    return res.stdout


def stop(name: str) -> None:
    run(STOP_CMD.format(name=name))


def kill(name: str) -> None:
    run(KILL_CMD.format(name=name))


def start(name: str) -> None:
    run(START_CMD.format(name=name))


def set_delay(name: str, delay_ms: int) -> None:
    """Перестворює екземпляр з ARTIFICIAL_DELAY_MS = delay_ms."""
    var = f"{name.upper()}_DELAY_MS"
    run(DELAY_CMD.format(name=name, delay=delay_ms), extra_env={var: str(delay_ms)})


# ---------------------------------------------------------------- конфігурація балансувальника

ALGORITHMS = {
    "roundrobin": "Round Robin: по черзі на кожен вузол",
    "leastconn": "Least Connections: на вузол з найменшою кількістю активних з'єднань",
    "weighted": "Weighted Round Robin: по черзі, пропорційно вагам вузлів",
    "source": "IP Hash: вузол визначається хешем IP клієнта (прив'язка клієнта до вузла)",
}

POOL_RE = re.compile(r"(    # >>> POOL[^\n]*\n)(.*?)(    # <<< POOL)", re.S)


def render_pool(algorithm: str, weights: list[int] | None = None) -> str:
    balance = {"weighted": "roundrobin"}.get(algorithm, algorithm)
    lines = [f"    balance {balance}"]
    if algorithm == "source":
        lines.append("    hash-type consistent")
    for i, name in enumerate(SERVERS):
        line = f"    server {name} {name}:8000"
        if algorithm == "weighted":
            w = (weights or [3, 1, 1])[i]
            line += f" weight {w}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def switch_algorithm(algorithm: str, weights: list[int] | None = None) -> None:
    """Переписує блок POOL у haproxy.cfg і робить безперервний reload (без розриву з'єднань)."""
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Невідомий алгоритм {algorithm}. Доступні: {', '.join(ALGORITHMS)}")
    text = LB_CONFIG.read_text(encoding="utf-8")
    new, n = POOL_RE.subn(lambda m: m.group(1) + render_pool(algorithm, weights) + m.group(3), text)
    if n != 1:
        raise RuntimeError("У haproxy.cfg не знайдено маркерів '# >>> POOL' / '# <<< POOL'")
    # Пишемо в той самий файл (той самий inode), щоб зміна була видна в контейнері.
    with open(LB_CONFIG, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    run(RELOAD_CMD)
    time.sleep(1.5)


def current_algorithm() -> str:
    m = POOL_RE.search(LB_CONFIG.read_text(encoding="utf-8"))
    body = m.group(2) if m else ""
    if "weight" in body:
        return "weighted"
    bal = re.search(r"balance (\w+)", body)
    return bal.group(1) if bal else "?"


# ---------------------------------------------------------------- статистика HAProxy

def pool_status() -> dict[str, str]:
    """Стан кожного вузла з точки зору балансувальника: UP, DOWN, MAINT..."""
    with urllib.request.urlopen(STATS_URL, timeout=3) as resp:
        raw = resp.read().decode()
    rows = csv.DictReader(io.StringIO(raw.lstrip("# ")))
    return {r["svname"]: r["status"] for r in rows
            if r["pxname"] == BACKEND and r["svname"] not in ("FRONTEND", "BACKEND")}


def wait_pool(expected_up: set[str], timeout: float = 90) -> None:
    """Чекає, поки health checks покажуть UP рівно для expected_up."""
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        try:
            last = pool_status()
            up = {n for n, s in last.items() if s.startswith("UP")}
            if up == expected_up:
                return
        except (urllib.error.URLError, OSError, KeyError):
            pass
        time.sleep(1)
    raise RuntimeError(f"Пул не прийшов до стану {sorted(expected_up)} за {timeout} с, зараз: {last}")


# ---------------------------------------------------------------- навантаження

@dataclass
class Sample:
    t: float          # секунда від початку тесту
    status: int       # HTTP-код; 0 = мережева помилка (клієнт не отримав відповіді)
    instance: str
    latency: float    # секунди


@dataclass
class LoadResult:
    samples: list[Sample] = field(default_factory=list)
    duration: float = 0.0

    @property
    def ok(self) -> list[Sample]:
        return [s for s in self.samples if 200 <= s.status < 400]

    @property
    def errors_5xx(self) -> int:
        return sum(1 for s in self.samples if s.status >= 500)

    @property
    def errors_net(self) -> int:
        return sum(1 for s in self.samples if s.status == 0)

    @property
    def rps(self) -> float:
        return len(self.ok) / self.duration if self.duration else 0.0

    def percentile(self, p: float) -> float:
        lat = sorted(s.latency for s in self.ok)
        if not lat:
            return 0.0
        k = max(0, min(len(lat) - 1, math.ceil(p / 100 * len(lat)) - 1))  # nearest-rank
        return lat[k] * 1000

    def distribution(self) -> Counter:
        return Counter(s.instance for s in self.ok)

    def distribution_str(self) -> str:
        dist, total = self.distribution(), len(self.ok) or 1
        return ", ".join(f"{k}: {v} ({v * 100 / total:.0f}%)" for k, v in sorted(dist.items()))


def one_request(url: str, timeout: float = 15) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"Connection": "close"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            return resp.status, resp.headers.get("X-Instance-ID", "?")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("X-Instance-ID", "?") if e.headers else "?"
    except (urllib.error.URLError, OSError):
        return 0, "-"


def run_load(path: str = DEFAULT_PATH, concurrency: int = 20, duration: float = 15,
             on_tick=None) -> LoadResult:
    """Закритий цикл: concurrency клієнтів безперервно шлють запити протягом duration секунд."""
    url = LB_URL + path
    result = LoadResult()
    lock = threading.Lock()
    t0 = time.perf_counter()
    deadline = t0 + duration

    def worker() -> None:
        while time.perf_counter() < deadline:
            start_t = time.perf_counter()
            status, inst = one_request(url)
            end_t = time.perf_counter()
            with lock:
                result.samples.append(Sample(start_t - t0, status, inst, end_t - start_t))

    ticker = None
    if on_tick:
        def tick_loop() -> None:
            sec = 0
            while time.perf_counter() < deadline:
                time.sleep(max(0.0, t0 + sec + 1 - time.perf_counter()))
                sec += 1
                on_tick(sec)
        ticker = threading.Thread(target=tick_loop, daemon=True)
        ticker.start()

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for _ in range(concurrency):
            pool.submit(worker)
    result.duration = time.perf_counter() - t0
    return result


def summary_row(label: str, r: LoadResult) -> str:
    return (f"| {label} | {len(r.samples)} | {r.rps:.1f} | {r.percentile(50):.0f} | {r.percentile(95):.0f} | "
            f"{r.percentile(99):.0f} | {r.errors_5xx + r.errors_net} | {r.distribution_str()} |")


SUMMARY_HEADER = ("| Конфігурація | Запитів | RPS | p50, мс | p95, мс | p99, мс | Помилки | Розподіл по вузлах |\n"
                  "|---|---|---|---|---|---|---|---|")


def docker_cpu_snapshot() -> dict[str, str]:
    """CPU кожного контейнера проєкту в момент виклику (для аналізу вузьких місць)."""
    try:
        out = run('docker stats --no-stream --format "{{.Name}};{{.CPUPerc}}"', check=False)
    except FileNotFoundError:
        return {}
    snap = {}
    for line in out.splitlines():
        name, _, cpu = line.partition(";")
        if name.startswith("globus-"):
            snap[name.replace("globus-", "").rsplit("-", 1)[0]] = cpu
    return snap


def save_results(name: str, markdown: str) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{name}.md"
    path.write_text(markdown, encoding="utf-8")
    return path
