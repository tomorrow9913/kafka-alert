# Alert

> 이 프로젝트는 카프카에서 수신된 메시지를 다양한 방법으로 처리할 수 있도록 합니다.

> [!IMPORTANT]
> 이 프로젝트에서는 후술할 처리 방식에 따라 특정 이름을 가진 kafka topic을 사용할 수 없습니다.

## How To Execute
```bash
docker compose pull # or docker compose up --build
docker compose up   # if you exec docker compuse up --build you can skip this
```

## Directory Struct
```bash
Alert
├── README.md                   # 설명을 위한 Readme 파일
├── requirements.txt            # 종속성 관리를 위한 파일
├── docker-compose.yml
├── dockerfile
├── Jenkinsfile                 # CICD를 위한 파일
├── main.py                     # 실행 파일
├── callback                    # callback 함수가 정의된 폴더
│   ├── __init__.py             # 무엇을 하려는지 정확히 모른다면 이 파일을 수정하지 마세요.
│   ├── all                     # 이곳에 파일을 등록하는 경우 정의된 모든 폴더에 적용됩니다.
│   │   └── example.py
│   └── topic_name              # 폴더명을 자유롭게 정의 가능(토픽 카프카 토픽 이름)
│       └── alert.py
├── log                         # 이곳에 실행 중 발생한 로그들이 저장됩니다.
│   └── monitor.log
└── utils
    ├── logger.py               # 로그 설정을 위한 파일
    └── queue_eventmanager.py   # 카프카와 관련된 파일
```

## How To Use
이 프로젝트 구조에서 새로운 처리를 추가하기 위해서는 두 가지 방법이 존재합니다.

1. 모든 토픽에 공통되는 처리 로직 추가
2. 특정 토픽에 공통되는 처리 로직 추가

두 가지 방식 모두 `callback` 이라는 이름을 가진 함수를 생성하는 방식으로 동일하게 추가할 수 있습니다.

`callback` 함수는 두 가지 매개변수를 받으며 리턴형은 존재하지 않습니다.

`callback` 함수는 카프카에서 메시지가 수신될 때 마다 카프카에서 전송된 메시지 key, value를 매개변수로 전달하여 해당 함수를 실행합니다.

예시 함수는 다음과 같습니다.

```py
async def callback(key, value: dict):
    print(f"key: {key}, value: {value}")
```

### Add all topic processing logic
만약 등록된 모든 토픽에 대해 동일한 처리를 하고 싶다면 `callback` **폴더**에 존재하는 `all` 폴더에 상기 함수가 포함된 python 파일을 추가하는 방식으로 처리 할 수 있습니다.

### Add specific topic processing logic 
1. 특정 토픽에 대해 처리를 추가하고 싶다면 `callback` **폴더**에 원하는 토픽 이름으로 폴더를 생성하고, 이곳에 상기 함수가 포함된 python 파일을 추가하는 방식으로 처리할 수 있습니다.
2. 만약 해당 토픽이 다른 로직 없이 공통 처리만 수행하고자 한다면, 폴더만 생성하여 등록 할 수 있습니다.

## Etc.
함수가 호출되는 순서는 토픽 처리가 먼저 수행된 뒤 이후 공통 처리 로직이 수행됩니다. 해당 부분을 수정하고 싶은 경우 `main.py`의 하기 된 부분을 수정하세요
```py
for topic in callbacks.keys():
    event_manager = EventManager(kafka_brokers, topic)
    
    callbacks[topic].extend(all_topic_sub_callbacks) # 이곳을 수정하세요
    for callback in callbacks[topic]:           
        logger.info(f"Subscribing {callback.name} to {topic} topic")
        event_manager.subscribe(callback.func, topic)
```

만약 특정 토픽에 대한 함수가 호출되는 순서를 조절하고 싶은 경우 `callback` 함수 정의와 함께 `Z_INDEX`를 설정할 수 있습니다.

정렬 방식을 변경하고 싶은 경우 `callback` **폴더**에 있는 `__init__.py`에서 정렬방식을 변경할 수 있습니다.

만약 특정 함수를 비활성화 하고 싶은 경우 `callback` 함수 정의와 함께 `ALERT_DISABLE`을 True로 설정하여 비활성화 할 수 있습니다.

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