# Current API Spec

## 문서 목적

현재까지 개발된 API 스펙과 기능을 정리한다.

앞으로 새로운 API가 추가되거나 기존 API의 request/response/payload가 변경되면 이 문서를 반드시 수정한다.

## 공통 기준

### Base URL

```text
http://{host}:{port}
```

로컬 개발 예시:

```text
http://127.0.0.1:18080
```

### Database configuration

The server does not contain a database connection default. `DATABASE_URL` must be provided through the process environment or the project `.env` file.

Docker 실행 시에는 `.env`를 이미지에 포함하지 않고 환경변수로 주입한다.

```bash
docker run --env-file .env -p 8000:8000 planner-agent
```

```text
DATABASE_URL=mysql+pymysql://<db-user>:<db-password>@<db-host>:3306/<db-name>
```

### 인증

REST API는 공통으로 아래 header가 필요하다.

```text
X-Device-Control-Key: {DEVICE_CONTROL_KEY}
```

`DEVICE_CONTROL_KEY`가 서버에 설정되지 않으면 REST API는 `503`을 반환한다.

header 값이 다르면 `401`을 반환한다.

### WebSocket 인증

WebSocket은 query parameter로 control key를 전달한다.

```text
ws://{host}:{port}/ws/boards/{board_id}?control_key={DEVICE_CONTROL_KEY}
```

key가 없거나 다르면 서버는 `1008` code로 연결을 닫는다.

장비별 키를 사용하려면 `DEVICE_CONTROL_KEYS` 환경 변수에 JSON object를 설정한다.

```text
{"container-01":"container-key","straight-01":"straight-key"}
```

설정된 장비별 키가 우선 적용되며, 해당 장비 키가 없으면 연결이 거부된다.

## 제어 대상

현재 seed 기준 제어 대상:

```text
container-01
straight-01
```

현재 board type:

```text
CONTAINER_CONVEYOR
STRAIGHT_CONVEYOR
```

## 공통 명령

현재 지원하는 기본 명령:

```text
SET_SPEED
FORWARD
REVERSE
STOP
EMERGENCY_STOP
RESET
STATUS_SYNC
RELEASE_EMERGENCY_STOP
SET_COLOR
RETURN_HOME
BOX_ACTION
```

현재 지원하는 capability 명령:

```text
SORT_COLOR
```

## 범용 Device API

범용 API는 board type과 관계없이 제어 대상을 조회하고 명령을 요청하는 API다.

### 제어 대상 목록 조회

```text
GET /api/devices
```

기능:

- 등록된 제어 대상 목록을 조회한다.

응답:

```json
[
  {
    "id": "container-01",
    "board_type": "CONTAINER_CONVEYOR",
    "name": "색상 분류 컨테이너",
    "enabled": true,
    "created_at": "ISO-8601",
    "updated_at": "ISO-8601"
  }
]
```

### 제어 대상 단건 조회

```text
GET /api/devices/{device_id}
```

기능:

- 제어 대상 기준 정보를 조회한다.

### 상태 조회

```text
GET /api/devices/{device_id}/state
```

기능:

- 현재 연결 상태, 실행 상태, 방향, 속도, 비상 상태를 조회한다.

응답:

```json
{
  "board_id": "container-01",
  "board_type": "CONTAINER_CONVEYOR",
  "name": "색상 분류 컨테이너",
  "connected": false,
  "run_status": "DISCONNECTED",
  "direction": "NONE",
  "current_speed": 0,
  "target_speed": 0,
  "running": false,
  "emergency_stopped": false,
  "last_command_id": null,
  "last_error_message": null,
  "last_seen_at": null,
  "state_updated_at": "ISO-8601"
}
```

### 지표 조회

```text
GET /api/devices/{device_id}/metrics
```

기능:

- 누적 가동 시간, 방향별 가동 시간, 명령 수, 실패 수, 비상정지 수를 조회한다.
- 동일 기능은 `operation_event` 도메인 API에서도 제공한다.

### 지표 초기화

```text
POST /api/devices/{device_id}/metrics/reset
```

기능:

- 제어 대상의 운영 지표를 초기화한다.
- 동일 기능은 `operation_event` 도메인 API에서도 제공한다.

### 이벤트 조회

```text
GET /api/devices/{device_id}/events?limit=50
```

기능:

- 제어 대상의 이벤트 이력을 조회한다.

query:

```text
limit: 1~200, default 50
```

동일 기능은 `operation_event` 도메인 API에서도 제공한다.

### 명령 이력 조회

```text
GET /api/devices/{device_id}/commands?limit=50
```

기능:

- 제어 대상의 명령 이력을 조회한다.

### 대기 중 명령 조회

```text
GET /api/devices/{device_id}/commands/pending?limit=50
```

기능:

- `REQUESTED`, `SENT`, `ACKED` 상태의 명령을 조회한다.

### 범용 명령 전송

```text
POST /api/devices/{device_id}/commands
```

기능:

- 제어 대상에 범용 명령을 요청한다.
- 서버는 명령을 DB에 기록하고 연결된 WebSocket session으로 ESP에 전달한다.
- ESP가 연결되어 있지 않으면 `409`를 반환한다.

요청:

```json
{
  "command": "SET_SPEED",
  "payload": {
    "speed": 120
  },
  "request_id": "optional-client-request-id"
}
```

응답:

```json
{
  "command_id": "cmd-id",
  "board_id": "container-01",
  "command": "SET_SPEED",
  "status": "SENT"
}
```

### 명령 수동 timeout

```text
POST /api/devices/{device_id}/commands/{command_id}/timeout
```

기능:

- 특정 명령을 수동으로 timeout 처리한다.

### 만료 명령 timeout 처리

```text
POST /api/devices/{device_id}/commands/timeout-expired
```

기능:

- ACK/RESULT timeout 기준을 넘은 명령을 timeout 처리한다.

### 진단 조회

```text
GET /api/devices/{device_id}/diagnostics
```

기능:

- 제어 대상의 readiness 판단에 필요한 상세 check를 조회한다.

주요 check:

```text
board_exists
state_exists
metric_exists
session_active
heartbeat_recent
no_pending_timeout
not_emergency_stopped
```

### readiness 조회

```text
GET /api/devices/{device_id}/diagnostics/readiness
```

기능:

- readiness 결과와 check 목록만 간단히 조회한다.

### ping 명령 전송

```text
POST /api/devices/{device_id}/diagnostics/ping
```

기능:

- `STATUS_SYNC` 명령을 전송해 장비 상태 동기화를 요청한다.

### 세션 이력 조회

```text
GET /api/devices/{device_id}/sessions?limit=50
```

기능:

- 제어 대상의 session 이력을 조회한다.

### stale session 검사

```text
POST /api/devices/{device_id}/sessions/check-stale
```

기능:

- heartbeat 기준으로 stale 여부를 검사하고 필요하면 상태를 갱신한다.

응답:

```json
{
  "board_id": "container-01",
  "stale": false
}
```

### capability 조회

```text
GET /api/devices/{device_id}/capabilities
```

기능:

- 제어 대상에 활성화된 capability 목록을 조회한다.

응답 예시:

```json
[
  {
    "id": 1,
    "board_id": "container-01",
    "capability_code": "COLOR_CLASSIFICATION",
    "code": "COLOR_CLASSIFICATION",
    "enabled": true,
    "commands": ["SORT_COLOR"],
    "payload_schema": {
      "required": ["color"],
      "properties": {
        "color": {
          "type": "string"
        }
      }
    }
  }
]
```

### capability 명령 전송

```text
POST /api/devices/{device_id}/capabilities/{capability_code}/commands
```

기능:

- 특정 capability 명령을 요청한다.

요청 예시:

```json
{
  "command": "SORT_COLOR",
  "payload": {
    "color": "RED"
  },
  "request_id": "optional-client-request-id"
}
```

현재 동작:

- `COLOR_CLASSIFICATION` capability는 `SORT_COLOR` 명령으로 처리한다.
- capability가 없으면 `404`를 반환한다.
- 필수 payload가 없으면 `400`을 반환한다.

### profile 조회

```text
GET /api/devices/{device_id}/profile
```

기능:

- 제어 대상의 operation profile을 조회한다.

응답 예시:

```json
{
  "device_id": "container-01",
  "profile_code": "classification-transfer",
  "operation_type": "CLASSIFICATION",
  "allowed_commands": [
    "SET_SPEED",
    "FORWARD",
    "REVERSE",
    "STOP",
    "RESET",
    "STATUS_SYNC",
    "RELEASE_EMERGENCY_STOP",
    "SORT_COLOR"
  ],
  "capabilities": ["COLOR_CLASSIFICATION"]
}
```

## Capability Management API

Capability Management API는 제어 대상에 붙는 부분 기능을 관리한다.

부분 기능은 board type에 고정하지 않고 device 단위로 등록한다.

### Device capability 목록 조회

```text
GET /api/capabilities/devices/{device_id}
```

기능:

- 특정 device에 등록된 capability 목록을 조회한다.

### Device capability 단건 조회

```text
GET /api/capabilities/devices/{device_id}/{capability_code}
```

기능:

- 특정 device에 등록된 capability 하나를 조회한다.

### Device capability 등록/수정

```text
PUT /api/capabilities/devices/{device_id}/{capability_code}
```

기능:

- 특정 device에 capability를 등록하거나 수정한다.
- path의 `{capability_code}`와 body의 `capability_code`가 다르면 `400`을 반환한다.

요청 예시:

```json
{
  "capability_code": "OBJECT_COUNTING",
  "commands": ["COUNT_OBJECT"],
  "payload_schema": {
    "required": []
  },
  "enabled": true
}
```

응답 예시:

```json
{
  "id": 2,
  "board_id": "straight-01",
  "capability_code": "OBJECT_COUNTING",
  "code": "OBJECT_COUNTING",
  "enabled": true,
  "commands": ["COUNT_OBJECT"],
  "payload_schema": {
    "required": []
  }
}
```

### Device capability 활성화/비활성화

```text
POST /api/capabilities/devices/{device_id}/{capability_code}/enable
POST /api/capabilities/devices/{device_id}/{capability_code}/disable
```

기능:

- 특정 device capability의 사용 여부를 변경한다.

## Operation Profile API

Operation Profile API는 device가 어떤 동작 묶음으로 운용되는지 관리한다.

현재 seed profile:

```text
classification-transfer
simple-transfer
```

### Operation profile 목록 조회

```text
GET /api/operation-profiles
```

기능:

- 등록된 operation profile 목록을 조회한다.

응답 예시:

```json
[
  {
    "code": "simple-transfer",
    "operation_type": "SIMPLE_TRANSFER",
    "enabled": true,
    "allowed_commands_json": [
      "SET_SPEED",
      "FORWARD",
      "REVERSE",
      "STOP",
      "RESET",
      "STATUS_SYNC",
      "RELEASE_EMERGENCY_STOP"
    ],
    "capabilities_json": [],
    "safety_policy_json": {}
  }
]
```

### Operation profile 단건 조회

```text
GET /api/operation-profiles/{profile_code}
```

기능:

- profile code 기준으로 operation profile을 조회한다.

### Operation profile 등록/수정

```text
PUT /api/operation-profiles/{profile_code}
```

기능:

- operation profile을 등록하거나 수정한다.
- path의 `{profile_code}`와 body의 `code`가 다르면 `400`을 반환한다.

요청 예시:

```json
{
  "code": "custom-transfer",
  "operation_type": "SIMPLE_TRANSFER",
  "allowed_commands": ["STOP"],
  "capabilities": [],
  "enabled": true,
  "safety_policy": {
    "emergency_stop_enabled": true
  }
}
```

### Device profile assignment 조회

```text
GET /api/operation-profiles/devices/{device_id}/assignment
```

기능:

- 특정 device에 할당된 operation profile을 조회한다.

응답 예시:

```json
{
  "device_id": "straight-01",
  "profile_code": "simple-transfer",
  "operation_type": "SIMPLE_TRANSFER",
  "allowed_commands": [
    "SET_SPEED",
    "FORWARD",
    "REVERSE",
    "STOP",
    "RESET",
    "STATUS_SYNC",
    "RELEASE_EMERGENCY_STOP"
  ],
  "capabilities": []
}
```

### Device profile assignment 변경

```text
PUT /api/operation-profiles/devices/{device_id}/assignment
```

기능:

- 특정 device에 operation profile을 할당한다.

요청 예시:

```json
{
  "profile_code": "custom-transfer"
}
```

## Operation Event API

Operation Event API는 device의 상태 변화, 명령 처리 이력에서 발생한 이벤트와 운영 지표를 조회한다.

### Device event 조회

```text
GET /api/operation-events/devices/{device_id}/events?limit=50
```

기능:

- device별 이벤트 이력을 조회한다.

query:

```text
limit: 1~200, default 50
```

응답 예시:

```json
[
  {
    "id": 1,
    "board_id": "container-01",
    "command_id": null,
    "event_type": "CONNECTED",
    "event_payload_json": {
      "session_id": "session-id"
    },
    "occurred_at": "ISO-8601"
  }
]
```

### Device metric 조회

```text
GET /api/operation-events/devices/{device_id}/metrics
```

기능:

- device별 누적 가동 시간, 방향별 가동 시간, 명령 수, 실패 수, 비상정지 수를 조회한다.

### Device metric 초기화

```text
POST /api/operation-events/devices/{device_id}/metrics/reset
```

기능:

- device별 운영 지표를 초기화한다.

## 기존 Container Conveyor API

기존 API는 호환성을 위해 유지한다.

prefix:

```text
/api/container-conveyors
```

### 조회 API

```text
GET /api/container-conveyors/{board_id}/status
GET /api/container-conveyors/{board_id}/metrics
GET /api/container-conveyors/{board_id}/events?limit=50
GET /api/container-conveyors/{board_id}/commands?limit=50
GET /api/container-conveyors/{board_id}/commands/pending?limit=50
GET /api/container-conveyors/{board_id}/diagnostics
GET /api/container-conveyors/{board_id}/diagnostics/readiness
```

### 명령 API

```text
POST /api/container-conveyors/{board_id}/commands/speed
POST /api/container-conveyors/{board_id}/commands/forward
POST /api/container-conveyors/{board_id}/commands/reverse
POST /api/container-conveyors/{board_id}/commands/stop
POST /api/container-conveyors/{board_id}/commands/sort-color
POST /api/container-conveyors/{board_id}/commands/reset
POST /api/container-conveyors/{board_id}/commands/status-sync
POST /api/container-conveyors/{board_id}/commands/release-emergency-stop
POST /api/container-conveyors/{board_id}/diagnostics/ping
```

speed 요청:

```json
{
  "speed": 120
}
```

sort color 요청:

```json
{
  "color": "RED"
}
```

### timeout/session/metric API

```text
POST /api/container-conveyors/{board_id}/commands/{command_id}/timeout
POST /api/container-conveyors/{board_id}/commands/timeout-expired
POST /api/container-conveyors/{board_id}/sessions/check-stale
POST /api/container-conveyors/{board_id}/metrics/reset
```

### 색상 분류 API

```text
GET    /api/container-conveyors/{board_id}/colors/counts
GET    /api/container-conveyors/{board_id}/colors/detections?limit=50
POST   /api/container-conveyors/{board_id}/colors/counts/reset
GET    /api/container-conveyors/{board_id}/color-rules
POST   /api/container-conveyors/{board_id}/color-rules
PUT    /api/container-conveyors/{board_id}/color-rules/{rule_id}
DELETE /api/container-conveyors/{board_id}/color-rules/{rule_id}
```

color rule 요청:

```json
{
  "color": "RED",
  "target_position": "LEFT",
  "enabled": true
}
```

## 기존 Straight Conveyor API

기존 API는 호환성을 위해 유지한다.

prefix:

```text
/api/straight-conveyors
```

### 조회 API

```text
GET /api/straight-conveyors/{board_id}/status
GET /api/straight-conveyors/{board_id}/metrics
GET /api/straight-conveyors/{board_id}/events?limit=50
GET /api/straight-conveyors/{board_id}/commands?limit=50
GET /api/straight-conveyors/{board_id}/commands/pending?limit=50
GET /api/straight-conveyors/{board_id}/diagnostics
GET /api/straight-conveyors/{board_id}/diagnostics/readiness
```

### 명령 API

```text
POST /api/straight-conveyors/{board_id}/commands/speed
POST /api/straight-conveyors/{board_id}/commands/forward
POST /api/straight-conveyors/{board_id}/commands/reverse
POST /api/straight-conveyors/{board_id}/commands/stop
POST /api/straight-conveyors/{board_id}/commands/reset
POST /api/straight-conveyors/{board_id}/commands/status-sync
POST /api/straight-conveyors/{board_id}/commands/release-emergency-stop
POST /api/straight-conveyors/{board_id}/diagnostics/ping
```

speed 요청:

```json
{
  "speed": 80
}
```

### timeout/session/metric API

```text
POST /api/straight-conveyors/{board_id}/commands/{command_id}/timeout
POST /api/straight-conveyors/{board_id}/commands/timeout-expired
POST /api/straight-conveyors/{board_id}/sessions/check-stale
POST /api/straight-conveyors/{board_id}/metrics/reset
```

## WebSocket API

### 초기 장비 등록 및 연결

서버에 `device_id`가 없는 ESP8266은 등록 전용 WebSocket으로 최초 연결한다.

```text
WS /ws/devices/connect?provisioning_key={DEVICE_PROVISIONING_KEY}
```

`provisioning_key`는 신규 장비 등록을 허용하는 별도 환경변수다. 일반 제어용 `DEVICE_CONTROL_KEY`와 분리한다.

연결 후 ESP는 첫 메시지로 반드시 `HELLO`를 전송한다.

```json
{
  "type": "HELLO",
  "device_id": "esp8266-84f3eb12abcd",
  "device_type": "STRAIGHT_CONVEYOR",
  "firmware_version": "1.0.0",
  "hardware_id": "84:F3:EB:12:AB:CD"
}
```

서버 처리:

```text
1. provisioning_key 검증
2. 첫 메시지가 HELLO인지 검증
3. device_id와 device_type 검증
4. 미등록 장비면 device, state, metric, profile 생성
5. 등록된 장비면 device_type 일치 여부 확인
6. WebSocket session 생성
7. WELCOME 응답
```

성공 응답:

```json
{
  "type": "WELCOME",
  "device_id": "esp8266-84f3eb12abcd",
  "device_type": "STRAIGHT_CONVEYOR",
  "session_id": "session-8f7...",
  "registered": true,
  "heartbeat_interval": 15
}
```

이미 등록된 장비를 다시 등록하면 `registered`는 `false`가 되며, 기존 장비 유형이 유지된다.

등록 후 ESP는 일반 제어 세션으로 재접속할 수 있다.

```text
WS /ws/boards/{device_id}?control_key={DEVICE_CONTROL_KEY}
```

등록 실패:

| 상황 | WebSocket 종료 code | reason |
|---|---:|---|
| provisioning key 누락 또는 불일치 | `1008` | `invalid provisioning key` |
| 첫 메시지가 HELLO가 아님 | `1008` | `first message must be HELLO` |
| device_id 누락, 빈 값 또는 64자 초과 | `1008` | `invalid device_id` |
| 지원하지 않는 device_type | `1008` | `unsupported device_type` |
| 기존 device_type과 불일치 | `1008` | `device_type does not match registered device` |

현재 지원하는 `device_type`은 다음과 같다.

```text
CONTAINER_CONVEYOR
STRAIGHT_CONVEYOR
```

### 장비 세션 연결

```text
WS /ws/boards/{board_id}?control_key={DEVICE_CONTROL_KEY}
```

#### 연결 방향

ESP8266이 WebSocket client가 되어 라즈베리 파이 서버에 연결한다.

```text
ESP8266 -> Raspberry Pi FastAPI WebSocket Server
```

#### 연결 요청

```text
GET /ws/boards/{board_id}?control_key={DEVICE_CONTROL_KEY}
Upgrade: websocket
Connection: Upgrade
```

`board_id`는 서버에 등록된 장비 식별자다. 현재 등록된 값은 다음과 같다.

```text
container-01
straight-01
```

#### 성공 응답

WebSocket upgrade가 성공하면 서버는 HTTP `101 Switching Protocols`로 응답하고 연결을 유지한다.

```text
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
```

서버는 연결 직후 임의의 명령을 보내지 않는다. ESP가 `HELLO`를 보내면 서버가 세션 정보를 `WELCOME`으로 반환한다.

```text
1. WebSocket upgrade 성공: HTTP 101
2. 서버가 board_id 기준 세션 생성
3. DB에 active session 저장
4. ESP가 HELLO 전송
5. 서버가 WELCOME(session_id) 전송
```

#### HELLO 요청

```json
{
  "type": "HELLO",
  "device_id": "container-01",
  "firmware_version": "1.0.0"
}
```

`device_id`는 선택 필드지만, 전달하는 경우 URL의 `board_id`와 같아야 한다.

#### WELCOME 성공 메시지

```json
{
  "type": "WELCOME",
  "device_id": "container-01",
  "session_id": "session-8f7...",
  "heartbeat_interval": 15
}
```

`session_id`는 연결마다 서버가 새로 생성하며, 이후 연결 이력 조회에 사용된다. 일반 명령 요청에는 `session_id`를 전달하지 않고 `device_id`를 사용한다.

#### 연결 실패 및 종료

| 상황 | 처리 | 클라이언트에서 확인할 값 |
|---|---|---|
| `control_key` 누락 또는 불일치 | 연결 거부 | WebSocket close `1008`, reason `invalid control key` |
| 장비별 인증 키 불일치 | 연결 거부 | WebSocket close `1008`, reason `invalid control key` |
| `HELLO.device_id`와 URL `board_id` 불일치 | 연결 종료 및 세션 비활성화 | WebSocket close `1008`, reason `device id mismatch` |
| 같은 `board_id`로 새 연결 | 기존 연결 종료, 새 연결 활성화 | 기존 연결 close `4000`, reason `reconnected` |
| 서버 또는 네트워크 접속 실패 | WebSocket upgrade 자체 실패 | 클라이언트 라이브러리의 connection error |
| 연결이 정상적으로 끊김 | 세션 비활성화 및 장비 상태 갱신 | 별도 응답 없음 |

인증 검증은 WebSocket upgrade 초기에 수행되므로 사용하는 서버/클라이언트 라이브러리에 따라 `1008` 대신 HTTP upgrade 거부로 보일 수 있다. 애플리케이션 의미는 동일하게 인증 실패다.

#### 연결 후 장비 메시지

연결이 성공한 뒤 ESP는 heartbeat, 상태, 명령 결과를 서버로 전송할 수 있다.

```text
HEARTBEAT
STATUS
ACK
RESULT
ERROR
COLOR_DETECTED
```

`HELLO` 없이 연결한 기존 client도 연결 자체와 명령 수신은 가능하지만, `session_id`를 받으려면 `HELLO`를 전송해야 한다.

연결 후 ESP가 `HELLO`를 보내면 서버는 현재 세션 ID를 `WELCOME`으로 응답한다. `HELLO` 없이 연결한 기존 클라이언트도 계속 명령을 수신할 수 있다.

ESP -> 서버:

```json
{
  "type": "HELLO",
  "device_id": "container-01",
  "firmware_version": "1.0.0"
}
```

서버 -> ESP:

```json
{
  "type": "WELCOME",
  "device_id": "container-01",
  "session_id": "session-...",
  "heartbeat_interval": 15
}
```

`HELLO.device_id`가 URL의 `board_id`와 다르면 서버는 `1008`로 연결을 종료한다.

### 연결 장비 조회

```text
GET /api/devices/connected
```

현재 활성 WebSocket 세션이 있는 장비만 반환한다.

### 연결 강제 종료

```text
POST /api/devices/{device_id}/sessions/disconnect
```

현재 WebSocket 연결을 서버에서 종료하고 세션을 `server_requested` 사유로 비활성화한다.

### 서버에서 ESP로 보내는 명령 message

```json
{
  "command_id": "cmd-id",
  "board_id": "container-01",
  "command": "SET_SPEED",
  "payload": {
    "speed": 120
  }
}
```

### ESP에서 서버로 보내는 message

ACK:

```json
{
  "type": "ACK",
  "command_id": "cmd-id"
}
```

RESULT:

```json
{
  "type": "RESULT",
  "command_id": "cmd-id",
  "status": "COMPLETED",
  "state": {
    "current_speed": 120
  }
}
```

STATUS:

```json
{
  "type": "STATUS",
  "status": "RUNNING",
  "state": {
    "direction": "FORWARD",
    "current_speed": 120,
    "running": true
  }
}
```

HEARTBEAT:

```json
{
  "type": "HEARTBEAT",
  "status": "ALIVE"
}
```

ERROR:

```json
{
  "type": "ERROR",
  "status": "EMERGENCY_STOPPED",
  "error_message": "emergency stop pressed"
}
```

COLOR_DETECTED:

```json
{
  "type": "COLOR_DETECTED",
  "status": "DETECTED",
  "color": "BLUE",
  "confidence": 0.91
}
```

## 주요 HTTP 응답

```text
200 OK
400 Bad Request
401 Unauthorized
404 Not Found
409 Conflict
422 Validation Error
503 Service Unavailable
```

주요 상황:

- 인증 header 누락/불일치: `401`
- `DEVICE_CONTROL_KEY` 미설정: `503`
- 제어 대상 없음: `404`
- board type 불일치: `400`
- ESP session 미연결 상태에서 명령 전송: `409`
- 비상 정지 중 허용되지 않은 명령 요청: `409`
- capability 없음: `404`
- payload 필수 값 누락: `400` 또는 `422`

## 현재 구현 상태

현재 구현된 API:

- 범용 device API
- capability management API
- operation profile API
- operation event API
- 기존 container conveyor API
- 기존 straight conveyor API
- board WebSocket session API

현재 제한:

- 기존 API는 호환성을 위해 유지 중이며, 내부적으로 DDD 도메인 구조를 사용한다.
- 명령 전송은 REST API로 요청하지만 실제 ESP 통신은 WebSocket session으로 수행한다.

## 문서 갱신 규칙

새 API를 추가할 때마다 반드시 이 문서를 수정한다.

수정 기준:

- endpoint 추가/삭제/변경
- request body 변경
- response body 변경
- 인증 방식 변경
- WebSocket message 변경
- command payload 변경
- capability/profile 정책 변경
