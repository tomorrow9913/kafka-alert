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
EMAIL_CONFIG__DEFAULT_SUBJECT="Alert Notification"
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

Kafka로 전달되는 알림 메시지는 아래 JSON 구조를 따라야 합니다. 메시지는 렌더링에 필요한 데이터와 어떤 알림 채널(Provider)로 보낼지에 대한 정보를 포함합니다.

### 기본 페이로드 구조

```json
{
  "provider": "discord",
  "destination": "https://discord.com/api/webhooks/...",
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

- `provider` (필수): 알림을 보낼 채널 (`discord`, `slack`, `email`).
- `destination` (선택): 알림을 보낼 주소 (Webhook URL, 이메일 주소 등). 생략 시 `.env` 설정에 따라 기본값으로 전송됩니다.
- `template` 또는 `template_content` (필수): 렌더링할 템플릿을 지정합니다.
  - `template`: `templates/` 폴더 내의 템플릿 파일 경로.
  - `template_content`: Jinja2 템플릿 문자열을 직접 전달.
- `data`: 템플릿 렌더링에 사용될 데이터 (객체).

---

### Provider별 페이로드 상세 가이드

#### 1. Discord & Slack

Discord와 Slack은 JSON 기반의 Webhook을 사용하므로, 템플릿은 최종적으로 **유효한 JSON 객체**를 생성해야 합니다.

- **파일 기반 (`template`)**:
  - `template` 경로의 파일은 Jinja2 문법으로 작성된 JSON이어야 합니다.
  - `discord` 프로바이더의 경우, 템플릿 이름 뒤에 `.json.j2`가 자동으로 추가될 수 있습니다. (예: `discord/error_report` -> `discord/error_report.json.j2`)

  ```json
  // Kafka Payload
  {
    "provider": "discord",
    "template": "discord/error_report",
    "data": { "service": "API", "msg": "DB Error" }
  }
  ```

- **직접 전달 (`template_content`)**:
  - `template_content`는 Jinja2 문법이 적용된 **JSON 문자열**이어야 합니다.
  - 이 문자열은 서버에서 렌더링된 후 JSON 객체로 파싱되어 Webhook으로 전송됩니다.

  ```json
  // Kafka Payload
  {
    "provider": "slack",
    "template_content": "{ \"text\": \"서비스: {{ service }} | 메시지: {{ msg }}\" }",
    "data": { "service": "Worker", "msg": "Queue full" }
  }
  ```

> [!TIP]
> Slack의 경우, 템플릿이 JSON이 아닌 일반 텍스트를 생성하면 `{"text": "생성된 텍스트"}` 형태로 자동 변환되는 Fallback 기능이 있습니다. 하지만 가급적 정확한 JSON 형태를 사용하는 것을 권장합니다.

#### 2. Email

Email 프로바이더는 템플릿으로 **이메일 본문(Body)**을 생성하고, 별도 필드를 통해 **제목(Subject)**을 지정합니다.

- **메일 제목(Subject) 지정**:
  메일 제목은 아래의 우선순위로 결정됩니다. `_mail_meta`를 통해 `subject`를 명시적으로 전달하는 것을 가장 권장합니다.
  1. `data._mail_meta.subject`: `data` 필드 내 `_mail_meta` 객체에 `subject` 키가 있을 경우 사용됩니다.
  2. `EMAIL_CONFIG__DEFAULT_SUBJECT` 환경 변수: `.env` 파일 또는 환경 변수에 `EMAIL_CONFIG__DEFAULT_SUBJECT`가 설정되어 있을 경우 사용됩니다.
  3. 기본값 ("Alert Notification"): 위 두 가지 모두 없을 경우 "Alert Notification"이 사용됩니다.

- **페이로드 예시**:
  - `template`은 HTML 본문을 생성하는 `email/alert.html.j2` 파일을 가리킵니다.
  - 메일 제목은 `data._mail_meta.subject` 필드를 통해 전달합니다.

  ```json
  {
    "provider": "email",
    "destination": ["dev@example.com", "ops@example.com"],
    "template": "email/alert",
    "data": {
      "_mail_meta": {
        "subject": "[긴급] 데이터베이스 연결 시간 초과"
      },
      "service": "Payment-API",
      "message": "프로덕션 데이터베이스에서 심각한 장애가 발생했습니다."
    }
  }
  ```

> [!NOTE]
> `data` 필드 내에서 `_`로 시작하는 모든 키(예: `_mail_meta`, `_hidden_sys_id`)는 템플릿 렌더링 컨텍스트에서 자동으로 제거됩니다. 특히 `_mail_meta`는 이메일의 `subject`, `cc`, `bcc`와 같은 메타데이터(headers)를 전달하는 데 사용됩니다.
