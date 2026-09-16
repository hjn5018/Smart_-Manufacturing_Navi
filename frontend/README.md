# Smart Manufacturing Navi - HTTP Prototype

React 한 화면에서 ESP-01 기반 설비를 HTTP로 제어하는 프로토타입입니다.

## 등록된 설비

- 기본 컨베이어: `10.34.129.169`
- 피더: `10.34.129.112`
- 색상분류 컨베이어: `10.34.129.108`
- AGV: 실행 화면 상단에서 ESP IP 입력 후 `IP 적용`

## 화면

- **대시보드**: 등록 설비 수, 연결 수, 가동 수, 설비 상태, 최근 제어 로그
- **설비 제어**: 각 설비 START/STOP, 방향, 속도, 색상분류, AGV 작업/복귀/적재함 제어

## 실행

```bash
npm install
npm run dev
```

React 실행 PC와 ESP-01들은 같은 네트워크에 있어야 합니다.

## AGV 코드

`arduino/agv_esp01.ino` : ESP-01 업로드 코드

`arduino/agv_uno.ino` : Arduino UNO 업로드 코드

### AGV UART 연결

- ESP TX -> Arduino D12 (SoftwareSerial RX)
- ESP RX <- Arduino D13 (SoftwareSerial TX)
- GND 공통
- Arduino D13은 5V 로직이므로 ESP RX 입력에는 3.3V 레벨 변환/저항 분압 권장

### AGV HTTP API

- `/start` : 한 사이클 시작
- `/stop` : 즉시 정지
- `/return` : 복귀 주행 시작
- `/box` : 적재함 서보 동작 후 복귀
- `/speed?value=1~100` : 주행 속도
- `/status` : 상태 JSON

> 웹의 전체 STOP은 소프트웨어 정지 기능입니다. 실제 산업용 비상정지는 별도의 하드웨어 안전회로가 필요합니다.
