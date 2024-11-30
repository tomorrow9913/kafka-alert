# Alert

> 이 프로젝트는 카프카에서 수신된 메시지를 다양한 방법으로 처리할 수 있도록 합니다.

## How To Execute
```bash
docker build -t alert .
docker run -e KAFKA_BROKERS=host1:port1,host2:port2,host3:port3 alert
```

## How To Use
이 프로젝트 구조에서 새로운 처리를 추가하기 위해서는 `callback` 폴더에 새로운 `*.py` 를 만듭니다.

이후 아래와 같이 `callback` 이라는 이름을 가진 함수를 생성합니다.

해당 `callback` 함수는 두 가지 매개변수를 받으며 리턴형은 존재하지 않습니다.

`callback` 함수는 카프카에서 메시지가 수신될 때 마다 카프카에서 전송된 메시지 key, value를 매개변수로 전달하여 해당 함수를 실행합니다.

예시 함수는 다음과 같습니다.

```py
async def callback(key, value: dict):
    print(f"key: {key}, value: {value}")
```

함수가 호출되는 순서를 조절하고 싶다면 `callback` **폴더**에 있는 `__init__.py`에서 정렬을 추가할 수 있습니다. 


만약 value가 json 임이 보장되지 않는 경우, 또는 바이너리가 전달될 수 있는 경우 아래를 수정하세요.
`utils` 폴더의 `queue_eventmanager.py`를 열어 `MessageQueue` class에 존재하는 `_create_consumer` 함수를 확인합니다.

```py
def _create_consumer(self):
    for attempt in range(self.max_retries):
        try:
            return KafkaConsumer(
                self.topic_name,
                bootstrap_servers=self.bootstrap_servers,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id=f'backend-{self.topic_name}-group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')), # 이곳을 수정합니다
                key_deserializer=lambda x: x.decode('utf-8'), # 바이너리 형식이 올 수 있는 경우 이곳을 수정합니다.
                session_timeout_ms=90000,  
                heartbeat_interval_ms=30000,
                request_timeout_ms=95000,
                connections_max_idle_ms=180000,
                max_poll_interval_ms=300000,
                api_version_auto_timeout_ms=60000,
                security_protocol='PLAINTEXT',
                fetch_max_wait_ms=500,
                fetch_min_bytes=1,
                fetch_max_bytes=52428800,
                metadata_max_age_ms=300000,
                reconnect_backoff_ms=5000,
                reconnect_backoff_max_ms=10000
            )
```