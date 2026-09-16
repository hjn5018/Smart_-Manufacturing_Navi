# operation_event

## 목적

장비 제어 중 발생한 이벤트와 운영 지표를 이력으로 저장하고 조회한다.

## 책임

- 명령 요청·전송·ACK·완료·실패 이력
- 장비 연결·해제 이력
- 상태 변경, 오류, 비상정지 이력
- capability 이벤트 이력
- 총 가동 시간과 방향별 가동 시간
- 명령 수, 완료 수, 실패 수, 비상정지 수, 오류 수 집계
- 이벤트와 지표 조회 및 초기화

## 주요 이벤트

```text
CONNECTED
DISCONNECTED
ERROR_OCCURRED
COLOR_DETECTED
EMERGENCY_STOPPED
METRICS_RESET
```

## API

```text
GET  /api/operation-events/devices/{device_id}/events
GET  /api/operation-events/devices/{device_id}/metrics
POST /api/operation-events/devices/{device_id}/metrics/reset
```

공통 장비 API에서도 동일한 이력을 조회할 수 있다.

```text
GET /api/devices/{device_id}/events
GET /api/devices/{device_id}/metrics
```

## 외부 연결

- 명령 결과와 장비 상태 변경은 `control_contract`에서 이벤트 기록 대상으로 전달된다.
- WebSocket 연결 이력은 `connection_session`의 세션 상태와 연계된다.
- capability 이벤트는 `capability_management`에서 전달된다.
