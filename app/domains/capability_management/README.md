# capability_management

## 목적

모든 장비에 공통으로 넣기 어려운 확장 기능과 capability별 payload 규격을 관리한다.

## 책임

- 장비별 capability 등록, 조회, 활성화, 비활성화
- capability별 허용 명령 관리
- capability별 payload schema 관리
- capability 명령 payload 생성 및 검증
- 색상 분류 capability의 색상 감지와 누적 수량 처리
- 색상별 분류 목적지 rule 관리

## 현재 capability

```text
COLOR_CLASSIFICATION
```

관련 명령:

```text
SORT_COLOR
```

## API

```text
GET  /api/capabilities/devices/{device_id}
GET  /api/capabilities/devices/{device_id}/{capability_code}
PUT  /api/capabilities/devices/{device_id}/{capability_code}
POST /api/capabilities/devices/{device_id}/{capability_code}/enable
POST /api/capabilities/devices/{device_id}/{capability_code}/disable
POST /api/devices/{device_id}/capabilities/{capability_code}/commands
```

컨테이너 분류 기능 API:

```text
GET  /api/container-conveyors/{board_id}/colors/counts
GET  /api/container-conveyors/{board_id}/colors/detections
POST /api/container-conveyors/{board_id}/colors/counts/reset
GET  /api/container-conveyors/{board_id}/color-rules
POST /api/container-conveyors/{board_id}/color-rules
PUT  /api/container-conveyors/{board_id}/color-rules/{rule_id}
DELETE /api/container-conveyors/{board_id}/color-rules/{rule_id}
```

## WebSocket 메시지

ESP는 색상 감지 시 다음 유형의 메시지를 보낸다.

```json
{
  "type": "COLOR_DETECTED",
  "board_id": "container-01",
  "color": "RED",
  "confidence": 0.98
}
```

## 외부 연결

- 공통 명령 전송과 세션은 `control_contract`, `connection_session`을 사용한다.
- 색상 감지 결과와 누적 지표는 `operation_event` 성격의 저장 구조를 사용한다.
