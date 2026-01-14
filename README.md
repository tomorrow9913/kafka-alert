# Universal Alert Platform (Kafka Alert System v2)

> 이 프로젝트는 카프카(Kafka)에서 수신된 메시지를 다양한 채널(Discord, Slack, Email 등)로 동적으로 처리하고 알림을 전송하는 유연한 플랫폼입니다.

> [!IMPORTANT]
> `all`이라는 이름의 카프카 토픽은 내부 로직(모든 토픽 공통 처리)을 위해 예약되어 있으므로 사용할 수 없습니다.

## Key Features
- **Provider Agnostic**: 비즈니스 로직 수정 없이 설정만으로 알림 채널(Discord 등)을 변경할 수 있습니다.
- **Template Driven**: Jinja2 템플릿 엔진을 사용하여 메시지 포맷을 자유롭게 정의할 수 있습니다.
- **High Concurrency**: `aiokafka`와 `asyncio`를 기반으로 하며, 세마포어(Semaphore)를 통한 동시성 제어로 높은 처리량을 보장합니다.
- **Configuration as Code**: `pydantic-settings`를 통해 환경 변수와 설정 파일을 타입 안전(Type-safe)하게 관리합니다.

## Prerequisites
- Python 3.12+
- Docker & Docker Compose

## Configuration (.env)
프로젝트 루트에 `.env` 파일을 생성하여 설정을 관리할 수 있습니다.

```env
# Application
APP_CONFIG__LOG_LEVEL=INFO
APP_CONFIG__LOG_DIR=logs

# Kafka
KAFKA_BROKERS=["localhost:9092"]
KAFKA_CONSUMER_GROUP=alert-group
KAFKA_MAX_CONCURRENT_TASKS=100

# Discord Provider
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

## How To Execute

### Using Docker Compose
```bash
docker compose up --build
```

### Local Development
```bash
# Install dependencies and create virtual environment
uv sync

# Run the application using uv
uv run main.py

# Run tests
uv run pytest
```

## Directory Structure
```bash
Alert
├── core/                   # 핵심 로직 (설정, 팩토리, 렌더러, 프로바이더)
│   ├── config.py           # Pydantic 기반 설정 관리
│   ├── factory.py          # 알림 처리 및 라우팅 로직
│   ├── renderer.py         # Jinja2 템플릿 렌더링 엔진
│   └── providers/          # 알림 채널 구현체 (Discord 등)
├── templates/              # 알림 메시지 템플릿 (JSON/HTML)
│   └── discord/
│       └── error_report.json.j2
├── callback/               # 비즈니스 로직 (토픽별 처리 핸들러)
│   ├── __init__.py         # 동적 모듈 로딩 로직
│   ├── all/                # 모든 토픽에 적용될 공통 핸들러
│   └── {topic_name}/       # 특정 토픽 전용 핸들러
├── utils/
│   ├── kafka_manager.py    # aiokafka 기반 Consumer/Producer 관리
│   └── logger.py           # loguru 기반 로깅 시스템
├── main.py                 # 애플리케이션 진입점
└── requirements.txt
```

## How To Use (Callback System)

새로운 알림 처리 로직을 추가하려면 `callback` 폴더에 Python 파일을 생성하면 됩니다.

### Callback Function Signature
콜백 함수는 `aiokafka.ConsumerRecord` 객체를 인자로 받으며, `async` 함수여야 합니다.

```python
from aiokafka import ConsumerRecord
from core.factory import factory
from utils.logger import LogManager

logger = LogManager.get_logger(__name__)

# 정렬 순서 (낮을수록 먼저 실행)
Z_INDEX = 0
# 비활성화 여부
ALERT_DISABLE = False

async def callback(msg: ConsumerRecord):
    """
    msg.value는 이미 JSON으로 역직렬화된 상태(dict)이거나, 
    실패 시 bytes 그대로일 수 있습니다.
    """
    logger.info(f"Received message on topic {msg.topic}")
    
    if isinstance(msg.value, dict):
        # AlertFactory를 통해 템플릿 렌더링 및 전송
        await factory.process(msg.value)
```

### 1. 모든 토픽 공통 처리
`callback/all/` 폴더에 Python 파일을 추가하세요.

### 2. 특정 토픽 전용 처리
`callback/{topic_name}/` 폴더를 생성하고 Python 파일을 추가하세요. Kafka 클러스터에 해당 토픽이 존재해야 구독이 시작됩니다.

## Message Protocol
Kafka 메시지 Payload 예시:
```json
{
  "provider": "discord",
  "template": "discord/error_report",
  "data": {
    "service": "Payment-API",
    "timestamp": "2024-01-14 12:00:00",
    "errors": [
      { "code": "500", "msg": "DB Connection Failed" }
    ]
  }
}
```
`core/factory.py`는 이 메시지를 받아 `templates/discord/error_report.json.j2` 템플릿을 렌더링하고 Discord로 전송합니다.