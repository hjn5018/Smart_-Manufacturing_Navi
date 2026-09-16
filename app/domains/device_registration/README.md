# device_registration

## 목적

서버에 식별자가 등록되지 않은 ESP8266을 최초 연결 시 장비로 등록하고, 등록 직후 제어 세션을 시작한다.

## 책임

- 최초 연결용 provisioning key 검증
- ESP가 전달한 `device_id`와 `device_type` 검증
- 신규 장비의 기본 정보, 상태, 지표, profile 생성
- 이미 등록된 장비의 재등록 여부 확인
- 등록 완료 후 `connection_session` 세션 연결

## 초기 연결

```text
WS /ws/devices/connect?provisioning_key={DEVICE_PROVISIONING_KEY}
```

첫 메시지:

```json
{
  "type": "HELLO",
  "device_id": "esp8266-84f3eb12abcd",
  "device_type": "STRAIGHT_CONVEYOR",
  "firmware_version": "1.0.0",
  "hardware_id": "84:F3:EB:12:AB:CD"
}
```

성공 응답:

```json
{
  "type": "WELCOME",
  "device_id": "esp8266-84f3eb12abcd",
  "device_type": "STRAIGHT_CONVEYOR",
  "session_id": "session-...",
  "registered": true,
  "heartbeat_interval": 15
}
```

## 지원 장비 유형

```text
CONTAINER_CONVEYOR
STRAIGHT_CONVEYOR
```

## 이후 연결

최초 등록이 완료된 장비는 다음 일반 세션 endpoint로 재접속한다.

```text
WS /ws/boards/{device_id}?control_key={DEVICE_CONTROL_KEY}
```

## 실패 처리

```text
1008 invalid provisioning key
1008 first message must be HELLO
1008 invalid device_id
1008 unsupported device_type
1008 device_type does not match registered device
```
