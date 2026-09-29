"""Process-wide singletons: adapter, memory service, LLM client, event pub/sub."""

from __future__ import annotations

import asyncio
import threading
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from .adapters.simulated import SimulatedAdapter
from .config import get_settings
from .llm.client import LLMClient
from .memory.schemas import BeliefSet
from .memory.service import MemoryEventPayload, MemoryService


@dataclass
class EventBus:
    """In-process fan-out for SSE subscribers. Also keeps last N events."""
    history: deque[MemoryEventPayload] = field(default_factory=lambda: deque(maxlen=500))
    subscribers: set[asyncio.Queue] = field(default_factory=set)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def publish(self, evt: MemoryEventPayload) -> None:
        with self.lock:
            self.history.append(evt)
            subs = list(self.subscribers)
        for q in subs:
            try:
                q.put_nowait(evt)
            except asyncio.QueueFull:
                pass

    async def subscribe(self) -> AsyncIterator[MemoryEventPayload]:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        with self.lock:
            self.subscribers.add(q)
        try:
            while True:
                evt = await q.get()
                yield evt
        finally:
            with self.lock:
                self.subscribers.discard(q)


class AppState:
    def __init__(self) -> None:
        self.event_bus = EventBus()
        self.adapter = SimulatedAdapter()
        self.llm = LLMClient()
        self.settings = get_settings()
        try:
            self.memory = MemoryService.from_env(event_sink=self.event_bus.publish)
        except Exception:
            self.memory = None  # Hindsight unreachable — routes fall back to memory-off.
        # Belief history: last computed BeliefSet per week, used for diff highlighting
        # when the UI advances weeks.
        self.beliefs_by_week: dict[int, BeliefSet] = {}
        # Last non-empty prioritise result per week. Reused when reflect
        # returns zero adjustments (LLM non-determinism) so the UI does not
        # oscillate between "memory reranked 6" and "memory reranked 0".
        self.last_adjustments_by_week: dict[int, dict[str, dict]] = {}

    def memory_available(self) -> bool:
        return self.memory is not None and bool(self.settings.hindsight_api_key)


_state: AppState | None = None


def get_state() -> AppState:
    global _state
    if _state is None:
        _state = AppState()
    return _state
