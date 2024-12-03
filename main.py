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
    topic = os.getenv("KAFKA_TOPIC")
    if not kafka_brokers:
        logger.error("No Kafka brokers configured, skipping event manager setup")
        exit(-1)
        
    logger.info("Initializing event manager")
    
    all_topic_sub_callbacks = callbacks.pop("all", [])
     
    event_manager = EventManager(kafka_brokers, list(callbacks.keys()))
    
    logger.info(f"Subscribing to callbacks : {callbacks.keys()}")
    for topic in callbacks.keys():
        callbacks[topic].extend(all_topic_sub_callbacks)
        for callback in callbacks[topic]:           
            logger.info(f"Subscribing [{topic}] {callback.name}-{callback.func}")
            event_manager.subscribe(callback.func, topic)
    try:
        logger.info("Starting event manager")
        await event_manager.start()
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down event manager")
    finally:
        logger.info("stop event manager")
        if event_manager:
            await event_manager.stop()

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        pass