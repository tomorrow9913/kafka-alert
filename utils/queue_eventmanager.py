from typing import Callable, List
import asyncio
import json
import time
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable
from contextlib import contextmanager

class EventBus:
    def __init__(self):
        self.subscribers: List[Callable] = []
    
    def subscribe(self, callback: Callable):
        """콜백 함수(async func) 등록"""
        self.subscribers.append(callback)
        return len(self.subscribers) - 1  # subscriber id 반환
    
    def unsubscribe(self, subscriber_id: int):
        """구독 취소"""
        if subscriber_id < 0 or subscriber_id >= len(self.subscribers):
            return False
        
        self.subscribers.pop(subscriber_id)
        return True

class MessageQueue:
    def __init__(self, kafka_brokers: str, topic_name: str, max_retries: int=3):
        self.max_retries = max_retries
        self.bootstrap_servers = kafka_brokers.split(",")
        self.topic_name = topic_name
        self.client = self._create_consumer()
    
    def _create_consumer(self):
        for attempt in range(self.max_retries):
            try:
                return KafkaConsumer(
                    self.topic_name,
                    bootstrap_servers=self.bootstrap_servers,
                    auto_offset_reset='earliest',
                    enable_auto_commit=True,
                    group_id=f'backend-{self.topic_name}-group',
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                    session_timeout_ms=90000,  # 세션 타임아웃 증가
                    heartbeat_interval_ms=30000,  # 하트비트 간격 증가
                    request_timeout_ms=95000,  # 요청 타임아웃 증가
                    connections_max_idle_ms=180000,
                    max_poll_interval_ms=300000,
                    api_version_auto_timeout_ms=60000,  # API 버전 체크 타임아웃 증가
                    security_protocol='PLAINTEXT',
                    fetch_max_wait_ms=500,
                    fetch_min_bytes=1,
                    fetch_max_bytes=52428800,
                    metadata_max_age_ms=300000,
                    reconnect_backoff_ms=5000,
                    reconnect_backoff_max_ms=10000
                )
            except NoBrokersAvailable:
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    time.sleep(wait_time)
                else:
                    raise
    @contextmanager
    def get_consumer(self):
        """컨슈머 컨텍스트 매니저"""
        try:
            yield self.client
        finally:
            self.close()
    
    def close(self):
        try:
            if self.client:
                self.client.close()
        except Exception as e:
            print(f"Error while closing consumer: {str(e)}")
        
class Consumer(MessageQueue):
    def __init__(self, kafka_broker: str, topic_name: str, event_bus: EventBus, max_retries=3):
        super().__init__(kafka_broker, topic_name, max_retries)
        self.event_bus = event_bus
        self.is_running = False

    async def start(self):
        async def run_consumer():
            while True:
                try:
                    message = await asyncio.to_thread(next, self.client)
                    if message:
                        key = message.key
                        value = message.value
                        if isinstance(value, str):
                            value = json.loads(value)
                        
                        await asyncio.gather(
                            *[callback(key, value) for callback in self.event_bus.subscribers]
                        )
                except Exception as e:
                    print(f"Error reading message {self.topic_name}: {e}")
                    await asyncio.sleep(1)
        
        # 백그라운드 태스크 생성
        self._consumer_task = asyncio.create_task(run_consumer())
    
    async def stop(self, topic: str):
        if hasattr(self, '_consumer_task'):
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

class EventManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EventManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, kafka_broker: str, topic_name: str, max_retries=3):
        if not hasattr(self, 'event_buses'):
            self.event_buses = {}
        if not hasattr(self, 'consumers'):
            self.consumers = {}
            self.consumer_tasks = {}
        
        if topic_name not in self.event_buses:
            self.event_buses[topic_name] = EventBus()
        self.consumers[topic_name] = Consumer(kafka_broker, topic_name, self.event_buses[topic_name], max_retries)

    async def start(self, topic_name: str):
        if not asyncio.get_event_loop().is_running():
            asyncio.run(self.consumers[topic_name].start())
        else:
            self.consumer_tasks[topic_name] = asyncio.create_task(self.consumers[topic_name].start())

    async def start_all(self):
        for topic_name in self.consumers:
            await self.start(topic_name)

    async def stop(self, topic_name: str):
        if topic_name in self.consumers:
            await self.consumers[topic_name].stop()
            if topic_name in self.consumer_tasks:
                await self.consumer_tasks[topic_name]

    async def stop_all(self):
        for topic_name in list(self.consumers.keys()):
            await self.stop(topic_name)

    def subscribe(self, callback: Callable, topic_name: str) -> int:
        print(f"subscribing {topic_name} to {callback.__name__}")
        return self.event_buses[topic_name].subscribe(callback)

    def unsubscribe(self, subscriber_id: int, topic_name: str) -> bool:
        print(f"unsubscribing {topic_name} to {subscriber_id}")
        return self.event_buses[topic_name].unsubscribe(subscriber_id)