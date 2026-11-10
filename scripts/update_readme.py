"""Вставляє результати експериментів з results/*.md у README.md між маркерами.

    python3 scripts/update_readme.py

Маркери в README: <!-- RESULTS:name --> ... <!-- /RESULTS:name -->, де name = ім'я файлу в results/.
"""

from __future__ import annotations

import re

from _lb import RESULTS_DIR, ROOT

readme = ROOT / "README.md"
text = readme.read_text(encoding="utf-8")
updated = []

for res in sorted(RESULTS_DIR.glob("*.md")):
    name = res.stem
    pattern = re.compile(rf"(<!-- RESULTS:{name} -->\n).*?(\n<!-- /RESULTS:{name} -->)", re.S)
    body = res.read_text(encoding="utf-8").strip()
    text, n = pattern.subn(lambda m: m.group(1) + body + m.group(2), text)
    if n:
        updated.append(name)

readme.write_text(text, encoding="utf-8")
print("Оновлено розділи:", ", ".join(updated) if updated else "нічого (немає файлів у results/)")
