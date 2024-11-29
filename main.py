import os

from utils.queue_eventmanager import EventManager
from callback import callbacks

event_manager = None

def lifecycle():
    global event_manager
    
    kafka_brokers = os.getenv("KAFKA_BROKERS")
    if not kafka_brokers:
        print("No Kafka brokers configured, skipping event manager setup")
        exit(-1)
    event_manager = EventManager(kafka_brokers, "alert")
    for callback in callbacks:
        event_manager.subscribe(callback, "alert")
    yield
    if event_manager:
        event_manager.stop("alert")

async def main():
    next(lifecycle())
    try:
        await event_manager.start("alert")
        while True:
            pass
    except KeyboardInterrupt:
        pass
    finally:
        next(lifecycle())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())