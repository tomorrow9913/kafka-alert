# Universal Alert Platform (Kafka Alert System v2)

> 이 프로젝트는 카프카(Kafka)에서 수신된 메시지를 다양한 채널(Discord, Slack, Email 등)로 동적으로 처리하고 알림을 전송하는 유연한 플랫폼입니다.

> [!IMPORTANT]
> `all`이라는 이름의 카프카 토픽은 내부 로직(모든 토픽 공통 처리)을 위해 예약되어 있으므로 **실제 Kafka 토픽 이름으로 사용할 수 없습니다.**

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

# Email (SMTP) Provider
EMAIL_CONFIG__SMTP_HOST=smtp.gmail.com
EMAIL_CONFIG__SMTP_PORT=587
EMAIL_CONFIG__SMTP_USER=your_email@gmail.com
EMAIL_CONFIG__SMTP_PASSWORD=your_app_password
EMAIL_CONFIG__USE_TLS=True
EMAIL_CONFIG__DEFAULT_FROM_EMAIL=alert-system@example.com
EMAIL_CONFIG__DEFAULT_TO_EMAIL=admin@example.com
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
│   ├── all/                # [예약] 구독 중인 모든 토픽에 적용될 공통 핸들러
│   └── {topic_name}/       # [개별] 특정 토픽 전용 핸들러
├── utils/
│   ├── kafka_manager.py    # aiokafka 기반 Consumer/Producer 관리
│   └── logger.py           # loguru 기반 로깅 시스템
├── main.py                 # 애플리케이션 진입점
└── requirements.txt
```

## How To Use (Callback System)

새로운 알림 처리 로직을 추가하려면 `callback` 폴더에 Python 파일을 생성하면 됩니다.

### Callback 구독 메커니즘
서버가 시작될 때(`main.py` 실행 시점), `callback` 폴더를 스캔하여 **존재하는 폴더 이름과 일치하는 Kafka 토픽**을 구독합니다.
- `callback/{topic_name}/` 폴더가 있으면 해당 토픽을 구독합니다.
- `callback/all/` 폴더에 있는 로직은 **위에서 구독하기로 결정된 모든 토픽**에 추가적으로 등록됩니다.

### 1. 개별 토픽 처리 (`callback/{topic_name}/`)
특정 토픽(`payment-errors`)의 메시지만 처리하고 싶다면 `callback/payment-errors/` 폴더를 만들고 스크립트를 추가하세요.

### 2. 모든 토픽 공통 처리 (`callback/all/`)
현재 구독 중인 **모든 토픽**의 메시지에 대해 공통적으로 수행해야 할 작업(예: 로깅, 감사 추적, 이메일 백업 전송 등)이 있다면 `callback/all/` 폴더에 스크립트를 추가하세요.

> [!NOTE]
> `all`은 실제 Kafka 토픽을 구독하는 것이 아니라, 애플리케이션 내부에서 **"구독된 모든 토픽의 이벤트 루프"**에 해당 콜백을 주입하는 역할을 합니다.

### 활용 예시 (Scenario)
**요구사항:**
- `payment` 토픽의 에러는 **Discord**로 알림을 보내고 싶다.
- `infrastructure` 토픽의 에러는 **Slack**으로 알림을 보내고 싶다.
- 단, **모든 종류의 에러**(`payment`, `infrastructure` 포함)는 **Email**로도 전송되어야 한다.

**구현 방법:**
1. `callback/payment/discord_handler.py`: Discord 전송 로직 작성
2. `callback/infrastructure/slack_handler.py`: Slack 전송 로직 작성
3. `callback/all/email_backup.py`: Email 전송 로직 작성

**결과:**
- `payment` 토픽 수신 시: `discord_handler` 실행 + `email_backup` 실행
- `infrastructure` 토픽 수신 시: `slack_handler` 실행 + `email_backup` 실행

---

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

## Message Protocol (Payload)

알림을 전송하기 위해 Kafka 메시지는 아래 두 가지 방식 중 하나로 템플릿을 지정해야 합니다.

### 1. 파일 기반 템플릿 (`template`)
서버의 `templates/` 폴더에 저장된 파일명을 사용합니다.

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

### 2. 직접 템플릿 전달 (`template_content`)
클라이언트가 UI 구조(Jinja2 문자열)를 직접 전달합니다. 배포 없이 동적으로 UI를 변경할 때 유용합니다.

```json
{
  "provider": "discord",
  "template_content": "{\"content\": \"🚨 **{{ service }}** 에서 에러 발생! {{ msg }}\"}",
  "data": {
    "service": "Auth-Module",
    "msg": "Invalid Token detected"
  }
}
```

> [!TIP]
> `discord`나 `slack` 프로바이더 사용 시 `template_content`는 유효한 JSON 문자열 형태여야 합니다. `email` 프로바이더는 일반 텍스트나 HTML 문자열을 지원합니다.

### 3. Email 전송 특화 (Subject & Body)
Email 프로바이더는 제목(Subject)이 필수입니다. 아래와 같이 `data` 필드 내에 `subject`를 포함하는 것을 권장합니다.

```json
{
  "provider": "email",
  "template": "email/alert.html.j2",
  "destination": "admin@example.com",
  "data": {
    "subject": "[Emergency] DB Connection Timeout",
    "service": "Payment-API",
    "message": "Critical failure in production DB."
  }
}
```

> [!NOTE]
> `destination`을 생략할 경우 설정된 `EMAIL_CONFIG__DEFAULT_TO_EMAIL` 주소로 발송됩니다.
