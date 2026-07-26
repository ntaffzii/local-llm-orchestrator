from __future__ import annotations

import time
from collections import deque
from typing import Any


class MetricsStore:
    """In-memory rolling record of inference requests.

    Holds recent per-request events (timestamp, model, latency, success) in a ring
    buffer and derives windowed summaries with real period-over-period deltas. State
    is per-process and resets on restart -- enough to power the console's traffic view
    without a datastore, and safe on a read-only container filesystem.
    """

    def __init__(self, maxlen: int = 5000) -> None:
        self.events: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def record(self, *, model: str, latency_ms: float, ok: bool, key: str = "anonymous") -> None:
        self.events.appendleft(
            {
                "at": time.time(),
                "model": str(model or "unknown"),
                "key": str(key or "anonymous"),
                "latency_ms": float(latency_ms),
                "ok": bool(ok),
            }
        )

    @staticmethod
    def _aggregate(events: list[dict[str, Any]]) -> dict[str, Any]:
        count = len(events)
        if not count:
            return {"requests": 0, "avg_latency_ms": 0.0, "p95_latency_ms": 0.0, "error_rate": 0.0}
        latencies = sorted(event["latency_ms"] for event in events)
        errors = sum(1 for event in events if not event["ok"])
        p95_index = min(count - 1, int(round(0.95 * (count - 1))))
        return {
            "requests": count,
            "avg_latency_ms": round(sum(latencies) / count, 1),
            "p95_latency_ms": round(latencies[p95_index], 1),
            "error_rate": round(errors / count, 4),
        }

    @staticmethod
    def _delta_pct(current: float, previous: float) -> float | None:
        # None means "no baseline" (nothing in the previous window), so the UI can show
        # a neutral state instead of a fabricated percentage.
        if previous == 0:
            return None
        return round((current - previous) / previous * 100, 1)

    def summary(self, window_seconds: float = 3600.0, buckets: int = 12) -> dict[str, Any]:
        now = time.time()
        window_seconds = max(1.0, float(window_seconds))
        buckets = max(1, int(buckets))
        current_events = [event for event in self.events if event["at"] >= now - window_seconds]
        previous_events = [
            event for event in self.events if now - 2 * window_seconds <= event["at"] < now - window_seconds
        ]
        current = self._aggregate(current_events)
        previous = self._aggregate(previous_events)

        by_model: dict[str, int] = {}
        by_key: dict[str, int] = {}
        for event in current_events:
            by_model[event["model"]] = by_model.get(event["model"], 0) + 1
            by_key[event.get("key", "anonymous")] = by_key.get(event.get("key", "anonymous"), 0) + 1

        series = [0] * buckets
        bucket_seconds = window_seconds / buckets
        for event in current_events:
            offset = int((now - event["at"]) / bucket_seconds)
            if 0 <= offset < buckets:
                series[buckets - 1 - offset] += 1

        return {
            "window_seconds": window_seconds,
            "total_recorded": len(self.events),
            "current": current,
            "previous": previous,
            "delta_pct": {
                "requests": self._delta_pct(current["requests"], previous["requests"]),
                "avg_latency_ms": self._delta_pct(current["avg_latency_ms"], previous["avg_latency_ms"]),
                "error_rate": self._delta_pct(current["error_rate"], previous["error_rate"]),
            },
            "by_model": dict(sorted(by_model.items(), key=lambda item: item[1], reverse=True)),
            "by_key": dict(sorted(by_key.items(), key=lambda item: item[1], reverse=True)),
            "series": series,
        }
