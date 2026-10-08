"""SecureFlow Server-Sent Events (SSE) Asynchronous Event Broker.

Enables real-time streaming of traffic state changes to connected browsers.
"""
import asyncio
import json
from typing import Any, AsyncGenerator, Dict, Set


class EventBroker:
    """In-memory Pub/Sub event broker for Server-Sent Events."""

    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """Subscribe to live system event broadcasts."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        try:
            while True:
                data = await queue.get()
                yield data
        except asyncio.CancelledError:
            pass
        finally:
            self._subscribers.discard(queue)

    def publish(self, event_type: str, payload: Any) -> None:
        """Broadcast an event to all connected subscribers."""
        payload_str = json.dumps(payload)
        sse_message = f"event: {event_type}\ndata: {payload_str}\n\n"

        for queue in list(self._subscribers):
            try:
                queue.put_nowait(sse_message)
            except (asyncio.QueueFull, Exception):
                pass


broker = EventBroker()
