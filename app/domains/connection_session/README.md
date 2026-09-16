# connection_session

## 목적

ESP8266 등 제어 대상과 서버 사이의 활성 연결 및 연결 이력을 관리한다.

## 책임

- WebSocket 연결 등록 및 해제
- 장비별 활성 세션 1개 관리
- 연결마다 `session_id` 생성
- 동일 장비 재접속 시 기존 세션 종료
- heartbeat와 마지막 수신 시각 관리
- stale 세션 비활성화
- 활성 세션으로 명령 payload 전달
- 서버 요청에 따른 강제 연결 종료

## 연결 규격

```text
WS /ws/boards/{board_id}?control_key={DEVICE_CONTROL_KEY}
```

연결 후 ESP가 `HELLO`를 보내면 서버가 `WELCOME`을 응답한다.

```json
{
  "type": "HELLO",
  "device_id": "container-01",
  "firmware_version": "1.0.0"
}
```

```json
{
  "type": "WELCOME",
  "device_id": "container-01",
  "session_id": "session-...",
  "heartbeat_interval": 15
}
```

## 세션 상태

```text
CONNECTED -> DISCONNECTED
CONNECTED -> STALE
```

## API

```text
GET  /api/devices/connected
GET  /api/devices/{device_id}/sessions
POST /api/devices/{device_id}/sessions/check-stale
POST /api/devices/{device_id}/sessions/disconnect
```

## 외부 연결

- WebSocket 진입점은 현재 `capability_management`의 presentation 라우터에 있다.
- 명령 생성은 `control_contract`가 담당하고, 세션 도메인은 전달 채널만 제공한다.
