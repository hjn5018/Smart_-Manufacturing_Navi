# control_contract

## 목적

모든 제어 대상이 공통으로 사용하는 장비 식별, 명령, 상태, 안전 제어 규격을 관리한다.

## 책임

- 장비 기본 정보와 활성화 상태 관리
- 공통 명령 접수 및 payload 전달
- 명령 상태 관리: `REQUESTED`, `SENT`, `ACKED`, `COMPLETED`, `FAILED`, `TIMEOUT`
- 운전 상태 관리: 연결, 방향, 속도, 운전, 비상정지, 오류
- 명령 전송 전 장비 활성화·연결·비상정지 상태 검증
- 공통 diagnostics와 readiness 제공

## 공통 명령

```text
SET_SPEED
FORWARD
REVERSE
STOP
RESET
STATUS_SYNC
RELEASE_EMERGENCY_STOP
```

## API

```text
GET  /api/devices
GET  /api/devices/{device_id}
GET  /api/devices/{device_id}/state
POST /api/devices/{device_id}/commands
GET  /api/devices/{device_id}/commands
GET  /api/devices/{device_id}/commands/pending
GET  /api/devices/{device_id}/diagnostics
GET  /api/devices/{device_id}/diagnostics/readiness
GET  /api/devices/connected
GET  /api/devices/{device_id}/sessions
POST /api/devices/{device_id}/sessions/disconnect
```

## 외부 연결

- 명령 전송은 `connection_session`의 활성 WebSocket 세션을 사용한다.
- 장비별 동작 차이는 `operation_profile`에서 검증한다.
- 이벤트와 운영 지표는 `operation_event`에 기록한다.
- 확장 기능은 `capability_management`에서 처리한다.
