from __future__ import annotations

import json
import queue
import threading
from collections.abc import Callable, Iterator
from typing import Any


_DONE = object()


def sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def stream_timeline_worker(
    *,
    start: dict[str, Any],
    run: Callable[[Callable[[dict[str, Any]], None]], dict[str, Any]],
    complete_meta: dict[str, Any] | None = None,
) -> Iterator[str]:
    events: queue.Queue[tuple[str, dict[str, Any]] | object] = queue.Queue()
    index = 0

    def emit_step(step: dict[str, Any]) -> None:
        nonlocal index
        index += 1
        events.put(("step", {"index": index, "step": step}))

    def worker() -> None:
        try:
            events.put(("start", start))
            result = run(emit_step)
            events.put(("complete", {**(complete_meta or {}), **result}))
        except Exception as exc:  # pragma: no cover - exercised through API smoke tests
            events.put(("error", {"error": str(exc)}))
        finally:
            events.put(_DONE)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    while True:
        item = events.get()
        if item is _DONE:
            break
        event, data = item
        yield sse_event(event, data)
