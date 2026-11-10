"""Live-переключення алгоритму балансування без зупинки сервісу.

    python3 scripts/lb_switch.py roundrobin
    python3 scripts/lb_switch.py leastconn
    python3 scripts/lb_switch.py weighted --weights 3,1,1
    python3 scripts/lb_switch.py source
    python3 scripts/lb_switch.py            # показати поточний

Скрипт змінює блок POOL у haproxy/haproxy.cfg і надсилає HAProxy сигнал HUP:
новий процес підхоплює конфігурацію, старий дообслуговує поточні з'єднання.
"""

from __future__ import annotations

import argparse

from _lb import ALGORITHMS, current_algorithm, switch_algorithm

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("algorithm", nargs="?", choices=list(ALGORITHMS))
parser.add_argument("--weights", help="ваги для weighted, напр. 3,1,1")
args = parser.parse_args()

if not args.algorithm:
    print(f"Поточний алгоритм: {current_algorithm()}")
else:
    weights = [int(w) for w in args.weights.split(",")] if args.weights else None
    switch_algorithm(args.algorithm, weights)
    print(f"Алгоритм змінено на {args.algorithm}: {ALGORITHMS[args.algorithm]}")
