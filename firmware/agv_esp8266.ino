#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <WebSocketsClient.h>

// ======================================================
// Wi-Fi
// ======================================================

const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ======================================================
// FastAPI
// ======================================================

const char* SERVER_HOST = "YOUR_PLANNER_SERVER_IP";
const uint16_t SERVER_PORT = 8000;

const char* PROVISIONING_KEY =
  "YOUR_DEVICE_PROVISIONING_KEY";

// 반드시 FastAPI .env의 DEVICE_CONTROL_KEY와 동일하게
const char* CONTROL_KEY =
  "YOUR_DEVICE_CONTROL_KEY";

const char* DEVICE_TYPE =
  "AGV";

const char* FIRMWARE_VERSION =
  "1.0.0";

// ======================================================
// HTTP Server
// ======================================================

ESP8266WebServer server(80);

// ======================================================
// WebSocket
// ======================================================

WebSocketsClient provisioningWs;
WebSocketsClient controlWs;

String provisioningPath;
String controlPath;

// ======================================================
// Device
// ======================================================

String macAddress;
String deviceId;

// ======================================================
// WebSocket 상태
// ======================================================

bool provisioningComplete = false;
bool switchToControlRequested = false;

bool controlStarted = false;
bool controlConnected = false;
bool controlReady = false;

// ======================================================
// Heartbeat
// ======================================================

unsigned long heartbeatIntervalMs = 15000;
unsigned long lastHeartbeat = 0;

// ======================================================
// 장비 상태
// ======================================================

bool running = false;

int currentSpeed = 50;

String currentState = "IDLE";
String currentDirection = "FORWARD";


// ======================================================
// Debug
//
// ESP TX -> UNO로 모든 메시지가 전달되므로
// DBG: prefix를 붙인다.
//
// UNO는 DBG:로 시작하면 제어 명령으로 해석하지 않으면 됨.
// ======================================================

void debugLog(const String& message) {

  Serial.print("DBG:");
  Serial.println(message);
}


// ======================================================
// UNO 명령 전달
// ======================================================

void sendUnoCommand(const String& command) {

  // 실제 UNO가 받을 명령
  Serial.println(command);

  debugLog("UNO_CMD=" + command);
}


// ======================================================
// MAC -> device_id
//
// FC:F5:C4:8A:12:FF
//
// ->
//
// esp8266-fcf5c48a12ff
// ======================================================

String makeDeviceId(String mac) {

  mac.replace(":", "");
  mac.toLowerCase();

  return "esp8266-" + mac;
}


// ======================================================
// 간단한 JSON String 값 읽기
//
// 별도 ArduinoJson 라이브러리 없이 사용하기 위한 함수
// ======================================================

String getJsonString(
  const String& json,
  const String& key
) {

  String token = "\"" + key + "\"";

  int keyPos = json.indexOf(token);

  if (keyPos < 0) {
    return "";
  }

  int colonPos = json.indexOf(':', keyPos);

  if (colonPos < 0) {
    return "";
  }

  int startQuote = json.indexOf('"', colonPos + 1);

  if (startQuote < 0) {
    return "";
  }

  int endQuote = json.indexOf('"', startQuote + 1);

  if (endQuote < 0) {
    return "";
  }

  return json.substring(
    startQuote + 1,
    endQuote
  );
}


// ======================================================
// JSON int 값 읽기
// ======================================================

int getJsonInt(
  const String& json,
  const String& key,
  int defaultValue
) {

  String token = "\"" + key + "\"";

  int keyPos = json.indexOf(token);

  if (keyPos < 0) {
    return defaultValue;
  }

  int colonPos = json.indexOf(':', keyPos);

  if (colonPos < 0) {
    return defaultValue;
  }

  int start = colonPos + 1;

  while (
    start < json.length() &&
    (
      json[start] == ' ' ||
      json[start] == '\t'
    )
  ) {
    start++;
  }

  int end = start;

  while (
    end < json.length() &&
    (
      isDigit(json[end]) ||
      json[end] == '-'
    )
  ) {
    end++;
  }

  if (end <= start) {
    return defaultValue;
  }

  return json.substring(start, end).toInt();
}


// ======================================================
// WELCOME 여부
// ======================================================

bool isWelcome(const String& message) {

  return
    message.indexOf("\"type\":\"WELCOME\"") >= 0 ||
    message.indexOf("\"type\": \"WELCOME\"") >= 0;
}


// ======================================================
// HTTP CORS
// ======================================================

void cors() {

  server.sendHeader(
    "Access-Control-Allow-Origin",
    "*"
  );
}


void replyText(const String& text) {

  cors();

  server.send(
    200,
    "text/plain",
    text
  );
}


// ======================================================
// STATUS -> FastAPI
// ======================================================

void sendStatus() {

  if (!controlReady) {
    return;
  }

  String status =
    currentState == "EMERGENCY_STOPPED"
      ? "EMERGENCY_STOPPED"
      : (running ? "RUNNING" : "STOPPED");

  String message = "{";

  message += "\"type\":\"STATUS\",";
  message += "\"status\":\"" + status + "\",";
  message += "\"state\":{";

  message +=
    "\"direction\":\"" +
    currentDirection +
    "\",";

  message +=
    "\"current_speed\":" +
    String(currentSpeed) +
    ",";

  message +=
    "\"running\":" +
    String(running ? "true" : "false");

  message += "}";

  message += "}";

  controlWs.sendTXT(message);

  debugLog("STATUS_TX=" + message);
}


// ======================================================
// ACK
// ======================================================

void sendAck(const String& commandId) {

  if (
    !controlReady ||
    commandId.length() == 0
  ) {
    return;
  }

  String message =
    "{\"type\":\"ACK\","
    "\"command_id\":\"" +
    commandId +
    "\"}";

  controlWs.sendTXT(message);

  debugLog("ACK=" + commandId);
}


// ======================================================
// RESULT
// ======================================================

void sendResult(
  const String& commandId
) {

  if (
    !controlReady ||
    commandId.length() == 0
  ) {
    return;
  }

  String message = "{";

  message += "\"type\":\"RESULT\",";
  message += "\"command_id\":\"" + commandId + "\",";
  message += "\"status\":\"COMPLETED\",";
  message += "\"state\":{";

  message +=
    "\"current_speed\":" +
    String(currentSpeed) +
    ",";

  message +=
    "\"direction\":\"" +
    currentDirection +
    "\",";

  message +=
    "\"running\":" +
    String(running ? "true" : "false");

  message += "}";

  message += "}";

  controlWs.sendTXT(message);

  debugLog("RESULT=" + commandId);
}


// ======================================================
// ERROR
// ======================================================

void sendCommandError(
  const String& messageText
) {

  if (!controlReady) {
    return;
  }

  String message =
    "{\"type\":\"ERROR\","
    "\"status\":\"FAILED\","
    "\"error_message\":\"" +
    messageText +
    "\"}";

  controlWs.sendTXT(message);
}


// ======================================================
// Heartbeat
// ======================================================

void sendHeartbeat() {

  if (!controlReady) {
    return;
  }

  String message =
    "{\"type\":\"HEARTBEAT\","
    "\"status\":\"ALIVE\"}";

  controlWs.sendTXT(message);

  debugLog("HEARTBEAT");
}


// ======================================================
// 장비 동작
// ======================================================

void commandStart() {

  running = true;
  currentState = "MISSION";
  currentDirection = "FORWARD";

  sendUnoCommand("START");
}


void commandStop() {

  running = false;
  currentState = "STOPPED";

  sendUnoCommand("STOP");
}


void commandEmergencyStop() {

  running = false;
  currentState = "EMERGENCY_STOPPED";

  sendUnoCommand("EMERGENCY_STOP");
}


void commandReturn() {

  running = true;
  currentState = "RETURNING";
  currentDirection = "REVERSE";

  sendUnoCommand("RETURN");
}


void commandBox() {

  sendUnoCommand("BOX");
}


void commandSpeed(int value) {

  value = constrain(
    value,
    1,
    100
  );

  currentSpeed = value;

  sendUnoCommand(
    "S:" + String(value)
  );
}


// ======================================================
// WebSocket 명령 처리
// ======================================================

void handleWebSocketCommand(
  const String& message
) {

  String command =
    getJsonString(
      message,
      "command"
    );

  String commandId =
    getJsonString(
      message,
      "command_id"
    );

  if (command.length() == 0) {
    return;
  }

  debugLog("WS_COMMAND=" + command);

  // ----------------------------------------------------
  // FORWARD
  //
  // 현재 UNO 프로토콜 START와 연결
  // ----------------------------------------------------

  if (command == "START" || command == "FORWARD") {

    sendAck(commandId);

    commandStart();

    sendResult(commandId);
    sendStatus();

    return;
  }


  // ----------------------------------------------------
  // REVERSE
  //
  // 기존 AGV 프로토콜의 RETURN에 매핑
  // ----------------------------------------------------

  if (command == "RETURN_HOME" || command == "REVERSE") {

    sendAck(commandId);

    commandReturn();

    sendResult(commandId);
    sendStatus();

    return;
  }


  // ----------------------------------------------------
  // STOP
  // ----------------------------------------------------

  if (command == "STOP") {

    sendAck(commandId);

    commandStop();

    sendResult(commandId);
    sendStatus();

    return;
  }


  // ----------------------------------------------------
  // EMERGENCY_STOP
  // ----------------------------------------------------

  if (command == "EMERGENCY_STOP") {

    sendAck(commandId);

    commandEmergencyStop();

    sendResult(commandId);
    sendStatus();

    return;
  }


  // ----------------------------------------------------
  // BOX_ACTION
  // ----------------------------------------------------

  if (command == "BOX_ACTION") {

    sendAck(commandId);

    commandBox();

    sendResult(commandId);
    sendStatus();

    return;
  }


  // ----------------------------------------------------
  // SET_SPEED
  //
  // payload:
  //
  // {
  //   "speed": 50
  // }
  // ----------------------------------------------------

  if (command == "SET_SPEED") {

    int speedValue =
      getJsonInt(
        message,
        "speed",
        currentSpeed
      );

    speedValue =
      constrain(
        speedValue,
        1,
        100
      );

    sendAck(commandId);

    commandSpeed(speedValue);

    sendResult(commandId);
    sendStatus();

    return;
  }


  // ----------------------------------------------------
  // STATUS_SYNC
  // ----------------------------------------------------

  if (command == "STATUS_SYNC") {

    sendAck(commandId);

    sendStatus();

    sendResult(commandId);

    return;
  }


  // ----------------------------------------------------
  // RESET
  // ----------------------------------------------------

  if (command == "RESET") {

    sendAck(commandId);

    running = false;
    currentState = "IDLE";

    sendUnoCommand("RESET");

    sendResult(commandId);
    sendStatus();

    return;
  }


  // ----------------------------------------------------
  // RELEASE_EMERGENCY_STOP
  // ----------------------------------------------------

  if (
    command ==
    "RELEASE_EMERGENCY_STOP"
  ) {

    sendAck(commandId);

    sendUnoCommand(
      "RELEASE_EMERGENCY_STOP"
    );

    running = false;
    currentState = "IDLE";

    sendResult(commandId);
    sendStatus();

    return;
  }


  debugLog(
    "UNKNOWN_COMMAND=" + command
  );

  sendCommandError(
    "unsupported command: " + command
  );
}


// ======================================================
// 등록 HELLO
// ======================================================

void sendProvisioningHello() {

  String message = "{";

  message += "\"type\":\"HELLO\",";
  message += "\"device_id\":\"" + deviceId + "\",";
  message += "\"device_type\":\"" + String(DEVICE_TYPE) + "\",";
  message += "\"firmware_version\":\"" + String(FIRMWARE_VERSION) + "\",";
  message += "\"hardware_id\":\"" + macAddress + "\"";

  message += "}";

  debugLog(
    "PROVISION_HELLO=" +
    message
  );

  provisioningWs.sendTXT(
    message
  );
}


// ======================================================
// 일반 제어 HELLO
// ======================================================

void sendControlHello() {

  String message = "{";

  message += "\"type\":\"HELLO\",";
  message += "\"device_id\":\"" + deviceId + "\",";
  message += "\"firmware_version\":\"" + String(FIRMWARE_VERSION) + "\"";

  message += "}";

  debugLog(
    "CONTROL_HELLO=" +
    message
  );

  controlWs.sendTXT(
    message
  );
}


// ======================================================
// Provisioning WebSocket Event
// ======================================================

void provisioningEvent(
  WStype_t type,
  uint8_t* payload,
  size_t length
) {

  switch (type) {

    case WStype_CONNECTED:

      debugLog(
        "PROVISION_WS_CONNECTED"
      );

      sendProvisioningHello();

      break;


    case WStype_TEXT: {

      String message =
        String((char*)payload);

      debugLog(
        "PROVISION_RX=" +
        message
      );

      if (isWelcome(message)) {

        provisioningComplete = true;

        switchToControlRequested =
          true;

        debugLog(
          "PROVISION_SUCCESS"
        );
      }

      break;
    }


    case WStype_DISCONNECTED:

      if (!provisioningComplete) {

        debugLog(
          "PROVISION_WS_DISCONNECTED"
        );
      }

      break;


    case WStype_ERROR:

      debugLog(
        "PROVISION_WS_ERROR"
      );

      break;


    default:
      break;
  }
}


// ======================================================
// 일반 제어 WebSocket Event
// ======================================================

void controlEvent(
  WStype_t type,
  uint8_t* payload,
  size_t length
) {

  switch (type) {

    // --------------------------------------------------
    // 연결 성공
    // --------------------------------------------------

    case WStype_CONNECTED:

      controlConnected = true;
      controlReady = false;

      debugLog(
        "CONTROL_WS_CONNECTED"
      );

      sendControlHello();

      break;


    // --------------------------------------------------
    // 서버 메시지
    // --------------------------------------------------

    case WStype_TEXT: {

      String message =
        String((char*)payload);

      debugLog(
        "CONTROL_RX=" +
        message
      );

      // WELCOME
      if (isWelcome(message)) {

        controlReady = true;

        int interval =
          getJsonInt(
            message,
            "heartbeat_interval",
            15
          );

        if (interval <= 0) {
          interval = 15;
        }

        heartbeatIntervalMs =
          (unsigned long)interval *
          1000UL;

        lastHeartbeat =
          millis();

        debugLog(
          "CONTROL_READY"
        );

        debugLog(
          "HEARTBEAT_INTERVAL=" +
          String(interval)
        );

        // 연결 직후 현재 상태 전송
        sendStatus();

        return;
      }

      // 서버 명령 처리
      handleWebSocketCommand(
        message
      );

      break;
    }


    // --------------------------------------------------

    case WStype_DISCONNECTED:

      controlConnected = false;
      controlReady = false;

      debugLog(
        "CONTROL_WS_DISCONNECTED"
      );

      break;


    case WStype_ERROR:

      debugLog(
        "CONTROL_WS_ERROR"
      );

      break;


    default:
      break;
  }
}


// ======================================================
// Provisioning 시작
// ======================================================

void startProvisioning() {

  provisioningPath =
    "/ws/devices/connect"
    "?provisioning_key=" +
    String(PROVISIONING_KEY);

  debugLog(
    "PROVISION_PATH=" +
    provisioningPath
  );

  provisioningWs.begin(
    SERVER_HOST,
    SERVER_PORT,
    provisioningPath.c_str()
  );

  provisioningWs.onEvent(
    provisioningEvent
  );

  // 등록 성공 전까지 네트워크가 잠깐 끊겼다면 재시도
  provisioningWs.setReconnectInterval(
    5000
  );
}


// ======================================================
// 일반 제어 WebSocket 시작
// ======================================================

void startControlWebSocket() {

  controlPath =
    "/ws/boards/" +
    deviceId +
    "?control_key=" +
    String(CONTROL_KEY);

  debugLog(
    "CONTROL_PATH=" +
    controlPath
  );

  controlStarted = true;

  controlWs.begin(
    SERVER_HOST,
    SERVER_PORT,
    controlPath.c_str()
  );

  controlWs.onEvent(
    controlEvent
  );

  // 이후 연결이 끊기면
  // provisioning이 아니라 control WS만 재접속
  controlWs.setReconnectInterval(
    5000
  );
}


// ======================================================
// HTTP
// ======================================================

void handleRoot() {

  cors();

  server.send(
    200,
    "text/html; charset=utf-8",

    "<!doctype html>"
    "<html>"
    "<head>"
    "<meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>AGV Control</title>"
    "</head>"

    "<body style='font-family:Arial;text-align:center;padding:30px'>"

    "<h2>AGV Control</h2>"

    "<p>"
    "<button onclick=\"fetch('/start')\">START</button> "
    "<button onclick=\"fetch('/stop')\">STOP</button>"
    "</p>"

    "<p>"
    "<button onclick=\"fetch('/return')\">RETURN</button> "
    "<button onclick=\"fetch('/box')\">BOX</button>"
    "</p>"

    "<p>"
    "Speed "
    "<input type='range' min='1' max='100' value='50' "
    "oninput=\"fetch('/speed?value='+this.value)\">"
    "</p>"

    "</body>"
    "</html>"
  );
}


void handleStart() {

  commandStart();

  replyText("START");

  sendStatus();
}


void handleStop() {

  commandStop();

  replyText("STOP");

  sendStatus();
}


void handleReturn() {

  commandReturn();

  replyText("RETURN");

  sendStatus();
}


void handleBox() {

  commandBox();

  replyText("BOX");
}


void handleSpeed() {

  if (!server.hasArg("value")) {

    cors();

    server.send(
      400,
      "text/plain",
      "Missing value"
    );

    return;
  }

  int value =
    constrain(
      server.arg("value").toInt(),
      1,
      100
    );

  commandSpeed(value);

  replyText(
    String(value)
  );

  sendStatus();
}


void handleStatus() {

  cors();

  String json = "{";

  json += "\"connected\":";
  json +=
    controlReady ?
    "true" :
    "false";

  json += ",\"running\":";
  json +=
    running ?
    "true" :
    "false";

  json +=
    ",\"speed\":" +
    String(currentSpeed);

  json +=
    ",\"state\":\"" +
    currentState +
    "\"";

  json +=
    ",\"device_id\":\"" +
    deviceId +
    "\"";

  json += "}";

  server.send(
    200,
    "application/json",
    json
  );
}


// ======================================================
// Setup
// ======================================================

void setup() {

  // ESP TX -> UNO SoftwareSerial RX
  Serial.begin(9600);

  delay(1000);

  debugLog(
    "ESP8266_START"
  );

  // ----------------------------------------------------
  // WiFi
  // ----------------------------------------------------

  WiFi.mode(WIFI_STA);

  delay(100);

  // ----------------------------------------------------
  // MAC / Device ID
  // ----------------------------------------------------

  macAddress =
    WiFi.macAddress();

  deviceId =
    makeDeviceId(
      macAddress
    );

  debugLog(
    "MAC=" +
    macAddress
  );

  debugLog(
    "DEVICE_ID=" +
    deviceId
  );

  debugLog(
    "DEVICE_TYPE=" +
    String(DEVICE_TYPE)
  );

  // ----------------------------------------------------
  // WiFi 연결
  // ----------------------------------------------------

  debugLog(
    "WIFI_CONNECTING"
  );

  WiFi.begin(
    WIFI_SSID,
    WIFI_PASSWORD
  );

  while (
    WiFi.status() !=
    WL_CONNECTED
  ) {

    delay(500);

    debugLog(".");
  }

  debugLog(
    "WIFI_CONNECTED"
  );

  debugLog(
    "IP=" +
    WiFi.localIP().toString()
  );

  debugLog(
    "GATEWAY=" +
    WiFi.gatewayIP().toString()
  );

  // ----------------------------------------------------
  // 기존 HTTP Server
  // ----------------------------------------------------

  server.on(
    "/",
    handleRoot
  );

  server.on(
    "/start",
    handleStart
  );

  server.on(
    "/stop",
    handleStop
  );

  server.on(
    "/return",
    handleReturn
  );

  server.on(
    "/box",
    handleBox
  );

  server.on(
    "/speed",
    handleSpeed
  );

  server.on(
    "/status",
    handleStatus
  );

  server.begin();

  debugLog(
    "HTTP_SERVER_STARTED"
  );

  // ----------------------------------------------------
  // 최초 등록
  // ----------------------------------------------------

  startProvisioning();
}


// ======================================================
// Loop
// ======================================================

void loop() {

  // 기존 HTTP
  server.handleClient();


  // ====================================================
  // 최초 등록
  // ====================================================

  if (!provisioningComplete) {

    provisioningWs.loop();
  }


  // ====================================================
  // 등록 성공 -> 일반 제어 WS 전환
  // ====================================================

  if (
    switchToControlRequested &&
    !controlStarted
  ) {

    switchToControlRequested = false;

    debugLog(
      "SWITCH_TO_CONTROL_WS"
    );

    provisioningWs.disconnect();

    delay(100);

    startControlWebSocket();
  }


  // ====================================================
  // 일반 제어 WS
  // ====================================================

  if (controlStarted) {

    controlWs.loop();
  }


  // ====================================================
  // Heartbeat
  // ====================================================

  if (controlReady) {

    unsigned long now =
      millis();

    if (
      now - lastHeartbeat >=
      heartbeatIntervalMs
    ) {

      lastHeartbeat = now;

      sendHeartbeat();
    }
  }
}
