import os
import asyncio

from utils.queue_eventmanager import EventManager
from utils.logger import setup_logging
from callback import callbacks

event_manager = None
logger = None

async def main():
    global logger
    global event_manager
    logger = setup_logging(__name__)
    
    kafka_brokers = os.getenv("KAFKA_BROKERS")
    if not kafka_brokers:
        logger.error("No Kafka brokers configured, skipping event manager setup")
        exit(-1)
        
    logger.info("Initializing event manager")
    event_manager = EventManager(kafka_brokers, "alert")
    
    logger.info("Subscribing to callbacks")
    for callback in callbacks:
        logger.info(f"Subscribing {callback} to alert topic")
        event_manager.subscribe(callback, "alert")
    
    try:
        logger.info("Starting event manager")
        await event_manager.start("alert")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down event manager")
    finally:
        logger.info("stop event manager")
        if event_manager:
            await event_manager.stop("alert")

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        pass