# operation_profile

## 목적

장비 유형별 허용 명령, capability 조합, 동작 정책을 정의하고 장비에 할당한다.

## 책임

- operation profile 등록 및 수정
- profile별 허용 명령 정의
- profile별 capability 조합 정의
- profile별 안전 정책 정의
- 장비와 profile의 할당 관리
- profile에 따른 장비별 명령 범위 결정

## 현재 profile

```text
classification-transfer
  대상: CONTAINER_CONVEYOR
  capability: COLOR_CLASSIFICATION

simple-transfer
  대상: STRAIGHT_CONVEYOR
  capability: 없음
```

## API

```text
GET /api/operation-profiles
GET /api/operation-profiles/{profile_code}
PUT /api/operation-profiles/{profile_code}
GET /api/operation-profiles/devices/{device_id}/assignment
PUT /api/operation-profiles/devices/{device_id}/assignment
```

## 장비별 동작 API

일반 1자형 컨베이어:

```text
POST /api/straight-conveyors/{board_id}/commands/speed
POST /api/straight-conveyors/{board_id}/commands/forward
POST /api/straight-conveyors/{board_id}/commands/reverse
POST /api/straight-conveyors/{board_id}/commands/stop
POST /api/straight-conveyors/{board_id}/commands/reset
POST /api/straight-conveyors/{board_id}/commands/status-sync
POST /api/straight-conveyors/{board_id}/commands/release-emergency-stop
```

## 외부 연결

- 명령 전달은 `control_contract`와 `connection_session`을 사용한다.
- capability 존재 여부와 조합은 `capability_management`와 연결된다.
