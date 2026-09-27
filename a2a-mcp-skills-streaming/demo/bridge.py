"""Run async network streams on one fresh loop; update Streamlit on its own thread."""
import asyncio
import queue
import threading

def sync_stream(factory):
    events = queue.Queue()
    stopped = threading.Event()
    done = object()
    async def consume():
        try:
            async for event in factory():
                if stopped.is_set(): break
                events.put(event)
        except Exception as exc:
            events.put(exc)
        finally:
            events.put(done)
    worker = threading.Thread(target=lambda: asyncio.run(consume()), daemon=True)
    worker.start()
    try:
        while True:
            item = events.get(timeout=120)
            if item is done: break
            if isinstance(item, Exception): raise item
            yield item
    finally:
        stopped.set()
        worker.join(timeout=1)
