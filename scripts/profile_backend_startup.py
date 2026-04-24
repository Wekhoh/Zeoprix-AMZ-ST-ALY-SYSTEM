"""Backend cold-start import profiler — Sprint 5 · C.7.

One-shot diagnostic: measures how long each top-level backend module takes
to import + how long `create_app()` takes to finish. Helps identify slow
imports for cold-start optimization.

Usage::

    PYTHONPATH=. python scripts/profile_backend_startup.py

Output::

    === Import timings (sorted desc) ===
    src.backend.app                    1240.5 ms
    src.rules.engine                    380.2 ms
    ...
    === Totals ===
    total_import_ms: 2100.8
    create_app_ms:    180.3
    grand_total_ms:  2281.1
"""

from __future__ import annotations

import importlib
import time
from typing import Callable

# Modules to time in order of import. Order matches roughly the backend
# startup import chain so downstream modules are reused from cache.
_MODULES: list[str] = [
    "src.config.settings",
    "src.config.logger",
    "src.data.db",
    "src.data.models",
    "src.data.parser",
    "src.rules.engine",
    "src.rules.asin_rules",
    "src.rules.keyword_rules",
    "src.ai.client",
    "src.ai.chat",
    "src.ai.analyzer",
    "src.ai.copilot",
    "src.analysis.truth_replay",
    "src.analysis.asin_analyzer",
    "src.backend.auth",
    "src.backend.database",
    "src.backend.models",
    "src.backend.copilot_chat",
    "src.backend.insights",
    "src.services.settings_service",
    "src.backend.workbench_payload",
    "src.backend.app",
]


def _timed(label: str, fn: Callable[[], object]) -> float:
    start = time.perf_counter()
    fn()
    return (time.perf_counter() - start) * 1000


def main() -> int:
    timings: list[tuple[str, float]] = []

    for mod in _MODULES:
        ms = _timed(mod, lambda m=mod: importlib.import_module(m))
        timings.append((mod, ms))

    # Call create_app() to measure route registration overhead.
    from src.backend.app import create_app  # already imported above

    create_ms = _timed("create_app()", lambda: create_app())

    total_import_ms = sum(ms for _, ms in timings)
    grand_total_ms = total_import_ms + create_ms

    print("=== Import timings (sorted desc) ===")
    print(f"{'module':<40} {'ms':>10}")
    print("-" * 52)
    for mod, ms in sorted(timings, key=lambda item: item[1], reverse=True):
        print(f"{mod:<40} {ms:>10.1f}")

    print()
    print("=== Totals ===")
    print(f"total_import_ms: {total_import_ms:>10.1f}")
    print(f"create_app_ms:   {create_ms:>10.1f}")
    print(f"grand_total_ms:  {grand_total_ms:>10.1f}")

    # Flag anything > 500ms as a candidate for lazy-import optimization
    slow = [(m, ms) for m, ms in timings if ms > 500]
    if slow:
        print()
        print("=== Slow imports (> 500ms) — candidates for lazy import ===")
        for mod, ms in slow:
            print(f"  {mod}: {ms:.1f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
