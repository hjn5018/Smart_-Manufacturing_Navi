#include <ESP8266WiFi.h>
#include <ESP8266WiFiMulti.h>
#include <ESP8266WebServer.h>
#include <WebSocketsClient.h>

ESP8266WiFiMulti wifiMulti;
WebSocketsClient provisioningWs;
WebSocketsClient controlWs;
ESP8266WebServer server(80);

// ======================================================
// Wi-Fi Candidates (2개의 후보 중 연결 가능한 AP 자동 접속)
// ======================================================

const char* WIFI_SSID_1 = "kenta";
const char* WIFI_PASSWORD_1 = "00001111";
const char* SERVER_HOST_1 = "172.20.10.13";

const char* WIFI_SSID_2 = "LLim";
const char* WIFI_PASSWORD_2 = "limche123";
const char* SERVER_HOST_2 = "172.21.134.80";

// ======================================================
// FastAPI
// ======================================================

const char* SERVER_HOST = SERVER_HOST_1;
String serverHost = SERVER_HOST_1;
const uint16_t SERVER_PORT = 8000;

const char* PROVISIONING_KEY = "planner-device-provisioning-key";
const char* CONTROL_KEY = "planner-device-control-key";
const char* DEVICE_TYPE = "CONTAINER_CONVEYOR";
const char* FIRMWARE_VERSION = "1.0.0";

String deviceId;
bool provisioningComplete = false;
bool startControlRequested = false;
bool controlStarted = false;
bool controlReady = false;

int currentSpeed = 50;
String currentDirection = "FORWARD";
String currentColor = "RED";
bool running = false;
bool emergencyStopped = false;

unsigned long heartbeatIntervalMs = 15000;
unsigned long lastHeartbeatMs = 0;

void debugLog(const String& message) {
  Serial.print("DBG:");
  Serial.println(message);
}

String makeDeviceId(String mac) {
  mac.replace(":", "");
  mac.toLowerCase();
  return "esp8266-" + mac;
}

String getJsonString(const String& json, const String& key) {
  String token = "\"" + key + "\"";
  int keyPos = json.indexOf(token);
  if (keyPos < 0) return "";
  int colonPos = json.indexOf(':', keyPos);
  if (colonPos < 0) return "";
  int startQuote = json.indexOf('"', colonPos + 1);
  if (startQuote < 0) return "";
  int endQuote = json.indexOf('"', startQuote + 1);
  if (endQuote < 0) return "";
  return json.substring(startQuote + 1, endQuote);
}

int getJsonInt(const String& json, const String& key, int defaultValue) {
  String token = "\"" + key + "\"";
  int keyPos = json.indexOf(token);
  if (keyPos < 0) return defaultValue;
  int colonPos = json.indexOf(':', keyPos);
  if (colonPos < 0) return defaultValue;
  int start = colonPos + 1;
  while (start < json.length() && (json[start] == ' ' || json[start] == '\t')) start++;
  int end = start;
  while (end < json.length() && (isDigit(json[end]) || json[end] == '-')) end++;
  return end > start ? json.substring(start, end).toInt() : defaultValue;
}

bool isWelcome(const String& message) {
  return message.indexOf("\"type\":\"WELCOME\"") >= 0 ||
         message.indexOf("\"type\": \"WELCOME\"") >= 0;
}

void sendAck(const String& commandId) {
  if (!controlReady || commandId.length() == 0) return;
  String message = "{\"type\":\"ACK\",\"command_id\":\"" + commandId + "\"}";
  controlWs.sendTXT(message);
}

void sendStatus() {
  if (!controlReady) return;
  String status = emergencyStopped ? "EMERGENCY_STOPPED" : (running ? "RUNNING" : "STOPPED");
  String message = "{\"type\":\"STATUS\",\"status\":\"" + status + "\",\"state\":{";
  message += "\"direction\":\"" + currentDirection + "\",";
  message += "\"current_speed\":" + String(currentSpeed) + ",";
  message += "\"target_speed\":" + String(currentSpeed) + ",";
  message += "\"running\":" + String(running ? "true" : "false") + ",";
  message += "\"color\":\"" + currentColor + "\",";
  message += "\"target_color\":\"" + currentColor + "\",";
  message += "\"emergency_stopped\":" + String(emergencyStopped ? "true" : "false");
  message += "}}";
  controlWs.sendTXT(message);
}

void sendResult(const String& commandId) {
  if (!controlReady || commandId.length() == 0) return;
  String message = "{\"type\":\"RESULT\",\"command_id\":\"" + commandId + "\",";
  message += "\"status\":\"COMPLETED\",\"state\":{";
  message += "\"current_speed\":" + String(currentSpeed) + ",";
  message += "\"direction\":\"" + currentDirection + "\",";
  message += "\"running\":" + String(running ? "true" : "false") + ",";
  message += "\"color\":\"" + currentColor + "\",";
  message += "\"target_color\":\"" + currentColor + "\",";
  message += "\"emergency_stopped\":" + String(emergencyStopped ? "true" : "false");
  message += "}}";
  controlWs.sendTXT(message);
}

void sendError(const String& commandId, const String& reason) {
  if (!controlReady) return;
  String message = "{\"type\":\"ERROR\",\"command_id\":\"" + commandId + "\",";
  message += "\"status\":\"FAILED\",\"error_message\":\"" + reason + "\"}";
  controlWs.sendTXT(message);
}

void handleWebSocketCommand(const String& message) {
  String command = getJsonString(message, "command");
  String commandId = getJsonString(message, "command_id");
  if (command.length() == 0) return;

  if (command == "EMERGENCY_STOP") {
    sendAck(commandId);
    running = false;
    emergencyStopped = true;
    Serial.println("STOP");
    sendResult(commandId);
    sendStatus();
    return;
  }

  if (command == "RELEASE_EMERGENCY_STOP") {
    sendAck(commandId);
    emergencyStopped = false;
    running = false;
    sendResult(commandId);
    sendStatus();
    return;
  }

  if (emergencyStopped) {
    sendError(commandId, "device is emergency stopped");
    return;
  }

  if (command == "START") {
    sendAck(commandId);
    running = true;
    Serial.println("START");
  } else if (command == "STOP") {
    sendAck(commandId);
    running = false;
    Serial.println("STOP");
  } else if (command == "FORWARD") {
    sendAck(commandId);
    running = true;
    currentDirection = "FORWARD";
    Serial.println("FORWARD");
    Serial.println("START");
  } else if (command == "REVERSE") {
    sendAck(commandId);
    running = true;
    currentDirection = "REVERSE";
    Serial.println("REVERSE");
    Serial.println("START");
  } else if (command == "SET_SPEED") {
    int speed = getJsonInt(message, "speed", -1);
    if (speed < 1 || speed > 100) {
      sendError(commandId, "SET_SPEED requires an integer between 1 and 100");
      return;
    }
    sendAck(commandId);
    currentSpeed = speed;
    Serial.println("S:" + String(currentSpeed));
  } else if (command == "SET_COLOR" || command == "SORT_COLOR") {
    String color = getJsonString(message, "color");
    color.toUpperCase();
    if (color != "RED" && color != "BLUE") {
      sendError(commandId, "SET_COLOR requires color RED or BLUE");
      return;
    }
    sendAck(commandId);
    currentColor = color;
    Serial.println("COLOR:" + color);
  } else if (command == "RESET") {
    sendAck(commandId);
    running = false;
    emergencyStopped = false;
    currentDirection = "FORWARD";
    Serial.println("STOP");
    Serial.println("FORWARD");
  } else if (command == "STATUS_SYNC") {
    sendAck(commandId);
  } else {
    sendError(commandId, "unsupported command: " + command);
    return;
  }

  sendResult(commandId);
  sendStatus();
}

void sendProvisioningHello() {
  String message = "{\"type\":\"HELLO\",\"device_id\":\"" + deviceId + "\",";
  message += "\"device_type\":\"" + String(DEVICE_TYPE) + "\",";
  message += "\"firmware_version\":\"" + String(FIRMWARE_VERSION) + "\",";
  message += "\"hardware_id\":\"" + WiFi.macAddress() + "\"}";
  provisioningWs.sendTXT(message);
}

void sendControlHello() {
  String message = "{\"type\":\"HELLO\",\"device_id\":\"" + deviceId + "\",";
  message += "\"firmware_version\":\"" + String(FIRMWARE_VERSION) + "\"}";
  controlWs.sendTXT(message);
}

void provisioningEvent(WStype_t type, uint8_t* payload, size_t length) {
  if (type == WStype_CONNECTED) {
    debugLog("PROVISION_WS_CONNECTED");
    sendProvisioningHello();
  } else if (type == WStype_TEXT) {
    String message = String((char*)payload);
    if (isWelcome(message)) {
      debugLog("PROVISION_WELCOME");
      provisioningComplete = true;
      startControlRequested = true;
      provisioningWs.disconnect();
    }
  }
}

void controlEvent(WStype_t type, uint8_t* payload, size_t length) {
  if (type == WStype_CONNECTED) {
    controlReady = false;
    debugLog("CONTROL_WS_CONNECTED");
    sendControlHello();
  } else if (type == WStype_TEXT) {
    String message = String((char*)payload);
    if (isWelcome(message)) {
      controlReady = true;
      int seconds = getJsonInt(message, "heartbeat_interval", 15);
      heartbeatIntervalMs = (unsigned long)max(seconds, 1) * 1000UL;
      lastHeartbeatMs = millis();
      debugLog("CONTROL_READY");
      sendStatus();
    } else {
      debugLog("CONTROL_COMMAND=" + getJsonString(message, "command"));
      handleWebSocketCommand(message);
    }
  } else if (type == WStype_DISCONNECTED) {
    controlReady = false;
    debugLog("CONTROL_WS_DISCONNECTED");
  }
}

void startProvisioning() {
  String path = "/ws/devices/connect?provisioning_key=" + String(PROVISIONING_KEY);
  provisioningWs.begin(serverHost.c_str(), SERVER_PORT, path.c_str());
  provisioningWs.onEvent(provisioningEvent);
  provisioningWs.setReconnectInterval(5000);
}

void startControl() {
  String path = "/ws/boards/" + deviceId + "?control_key=" + String(CONTROL_KEY);
  controlWs.begin(serverHost.c_str(), SERVER_PORT, path.c_str());
  controlWs.onEvent(controlEvent);
  controlWs.setReconnectInterval(5000);
  controlStarted = true;
}


// ======================================================
// WEB PAGE
// ======================================================

const char MAIN_page[] PROGMEM = R"=====(
<!DOCTYPE html>
<html>

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Color Sorting Conveyor</title>

<style>

body {
    font-family: Arial, sans-serif;
    background: #f3f3f3;
    text-align: center;
    margin-top: 30px;
}

.container {
    width: 380px;
    max-width: 90%;
    margin: auto;
    background: white;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0 3px 15px #aaa;
}

h1 {
    font-size: 23px;
}

.section {
    margin-top: 25px;
    border-top: 1px solid #ddd;
    padding-top: 20px;
}

.speed {
    font-size: 36px;
    font-weight: bold;
    margin: 15px;
}

input[type=range] {
    width: 90%;
}

button {
    width: 140px;
    height: 48px;
    margin: 6px;
    border: 0;
    border-radius: 9px;
    font-size: 16px;
    cursor: pointer;
}

.start {
    background: #4CAF50;
    color: white;
}

.stop {
    background: #f44336;
    color: white;
}

.direction {
    background: #2196F3;
    color: white;
}

.red {
    background: #e53935;
    color: white;
}

.blue {
    background: #1976D2;
    color: white;
}

.status {
    margin-top: 15px;
    font-size: 17px;
}

</style>
</head>

<body>

<div class="container">

<h1>컬러 분류 컨베이어</h1>

<div class="section">

<button class="start" onclick="startMotor()">
START
</button>

<button class="stop" onclick="stopMotor()">
STOP
</button>

<div id="runStatus" class="status">
상태 : 정지
</div>

</div>


<div class="section">

<h3>컨베이어 방향</h3>

<button class="direction" onclick="forwardMotor()">
FORWARD
</button>

<button class="direction" onclick="reverseMotor()">
REVERSE
</button>

<div id="directionStatus" class="status">
방향 : 정방향
</div>

</div>


<div class="section">

<h3>속도</h3>

<div class="speed" id="speedValue">
50
</div>

<input
type="range"
min="1"
max="100"
value="50"
oninput="changeSpeed(this.value)"
>

</div>


<div class="section">

<h3>분류할 색상</h3>

<button class="red" onclick="selectColor('RED')">
RED
</button>

<button class="blue" onclick="selectColor('BLUE')">
BLUE
</button>

<div id="colorStatus" class="status">
분류 대상 : 빨간색
</div>

</div>

</div>


<script>

let speedTimer;


// ======================================================
// START
// ======================================================

function startMotor() {

    fetch("/start")
    .then(response => response.text())
    .then(() => {

        document.getElementById("runStatus").innerHTML =
            "상태 : 동작중";

    })
    .catch(() => {

        document.getElementById("runStatus").innerHTML =
            "상태 : 통신 오류";

    });
}


// ======================================================
// STOP
// ======================================================

function stopMotor() {

    fetch("/stop")
    .then(response => response.text())
    .then(() => {

        document.getElementById("runStatus").innerHTML =
            "상태 : 정지";

    });
}


// ======================================================
// FORWARD
// ======================================================

function forwardMotor() {

    fetch("/forward")
    .then(() => {

        document.getElementById("directionStatus").innerHTML =
            "방향 : 정방향";

    });
}


// ======================================================
// REVERSE
// ======================================================

function reverseMotor() {

    fetch("/reverse")
    .then(() => {

        document.getElementById("directionStatus").innerHTML =
            "방향 : 역방향";

    });
}


// ======================================================
// SPEED
// ======================================================

function changeSpeed(value) {

    document.getElementById("speedValue").innerHTML = value;

    clearTimeout(speedTimer);

    speedTimer = setTimeout(function() {

        fetch("/speed?value=" + value);

    }, 150);
}


// ======================================================
// COLOR
// ======================================================

function selectColor(color) {

    fetch("/color?value=" + color)
    .then(() => {

        if(color === "RED") {

            document.getElementById("colorStatus").innerHTML =
                "분류 대상 : 빨간색";

        } else {

            document.getElementById("colorStatus").innerHTML =
                "분류 대상 : 파란색";
        }

    });
}

</script>

</body>
</html>
)=====";


// ======================================================
// CORS
// ======================================================

void addCorsHeader() {

  server.sendHeader(
    "Access-Control-Allow-Origin",
    "*"
  );
}


// ======================================================
// ROOT
// ======================================================

void handleRoot() {

  addCorsHeader();

  server.send(
    200,
    "text/html; charset=utf-8",
    MAIN_page
  );
}


// ======================================================
// START
// ======================================================

void handleStart() {

  running = true;

  Serial.println("START");
  sendStatus();

  addCorsHeader();

  server.send(
    200,
    "text/plain",
    "START"
  );
}


// ======================================================
// STOP
// ======================================================

void handleStop() {

  running = false;

  Serial.println("STOP");
  sendStatus();

  addCorsHeader();

  server.send(
    200,
    "text/plain",
    "STOP"
  );
}


// ======================================================
// FORWARD
// ======================================================

void handleForward() {

  running = true;
  currentDirection = "FORWARD";

  Serial.println("FORWARD");
  Serial.println("START");
  sendStatus();

  addCorsHeader();

  server.send(
    200,
    "text/plain",
    "FORWARD"
  );
}


// ======================================================
// REVERSE
// ======================================================

void handleReverse() {

  running = true;
  currentDirection = "REVERSE";

  Serial.println("REVERSE");
  Serial.println("START");
  sendStatus();

  addCorsHeader();

  server.send(
    200,
    "text/plain",
    "REVERSE"
  );
}


// ======================================================
// SPEED
// 웹 1~100을 Arduino로 그대로 전달
// Arduino에서 microsecond delay로 변환
// ======================================================

void handleSpeed() {

  if (!server.hasArg("value")) {

    addCorsHeader();

    server.send(
      400,
      "text/plain",
      "Missing value"
    );

    return;
  }

  int value = server.arg("value").toInt();

  value = constrain(
    value,
    1,
    100
  );

  currentSpeed = value;

  Serial.print("S:");
  Serial.println(value);
  sendStatus();

  addCorsHeader();

  server.send(
    200,
    "text/plain",
    String(value)
  );
}


// ======================================================
// COLOR
// ======================================================

void handleColor() {

  if (!server.hasArg("value")) {

    addCorsHeader();

    server.send(
      400,
      "text/plain",
      "Missing value"
    );

    return;
  }

  String color = server.arg("value");

  color.toUpperCase();

  if (color == "RED") {

    currentColor = "RED";

    Serial.println("COLOR:RED");
    sendStatus();

  }

  else if (color == "BLUE") {

    currentColor = "BLUE";

    Serial.println("COLOR:BLUE");
    sendStatus();

  }

  else {

    addCorsHeader();

    server.send(
      400,
      "text/plain",
      "Invalid color"
    );

    return;
  }

  addCorsHeader();

  server.send(
    200,
    "text/plain",
    currentColor
  );
}


// ======================================================
// STATUS
// ======================================================

void handleStatus() {

  addCorsHeader();

  String json = "{";

  json += "\"connected\":";
  json += controlReady ? "true" : "false";
  json += ",";
  json += "\"running\":";
  json += running ? "true" : "false";
  json += ",";

  json += "\"speed\":";
  json += String(currentSpeed);
  json += ",";

  json += "\"direction\":\"";
  json += currentDirection;
  json += "\",";

  json += "\"color\":\"";
  json += currentColor;
  json += "\"";

  json += "}";

  server.send(
    200,
    "application/json",
    json
  );
}


// ======================================================
// SETUP
// ======================================================

void setup() {

  // ESP TX/RX UART
  // Arduino와 9600 baud 통신
  Serial.begin(9600);

  delay(1000);

  // ====================================================
  // Wi-Fi
  // ====================================================

  WiFi.mode(WIFI_STA);
  wifiMulti.addAP(WIFI_SSID_1, WIFI_PASSWORD_1);
  wifiMulti.addAP(WIFI_SSID_2, WIFI_PASSWORD_2);

  while (wifiMulti.run() != WL_CONNECTED) {

    delay(500);
  }
  deviceId = makeDeviceId(WiFi.macAddress());
  String localIp = WiFi.localIP().toString();
  if (WiFi.SSID() == WIFI_SSID_2) {
    serverHost = SERVER_HOST_2;
  } else {
    serverHost = SERVER_HOST_1;
  }
  Serial.println("WIFI:CONNECTED");
  Serial.println("IP:" + localIp);
  debugLog("WIFI_SSID=" + WiFi.SSID());
  debugLog("DEVICE_ID=" + deviceId);
  debugLog("SERVER_HOST=" + serverHost);
  
  delay(100);

  // ====================================================
  // HTTP API
  // ====================================================

  server.on("/", handleRoot);
  server.on("/start", handleStart);
  server.on("/stop", handleStop);
  server.on("/forward", handleForward);
  server.on("/reverse", handleReverse);
  server.on("/speed", handleSpeed);
  server.on("/color", handleColor);
  server.on("/status", handleStatus);

  server.begin();
  startProvisioning();
}


// ======================================================
// LOOP
// ======================================================

void loop() {

  if (wifiMulti.run() != WL_CONNECTED) {
    delay(10);
    return;
  }

  server.handleClient();
  if (!provisioningComplete) provisioningWs.loop();
  if (startControlRequested) {
    startControlRequested = false;
    startControl();
  }
  if (controlStarted) controlWs.loop();

  if (controlReady && millis() - lastHeartbeatMs >= heartbeatIntervalMs) {
    String heartbeat = "{\"type\":\"HEARTBEAT\",\"status\":\"ALIVE\"}";
    controlWs.sendTXT(heartbeat);
    lastHeartbeatMs = millis();
  }
}


//#include <ESP8266WiFi.h>
//
//const char* ssid = "kenta";
//const char* password = "00001111";
//
//void setup() {
//
//  Serial.begin(115200);
//  delay(2000);
//
//  Serial.println();
//  Serial.println("===== ESP8266 WiFi Test =====");
//
//  WiFi.mode(WIFI_STA);
//
//  // 이전 Wi-Fi 정보 제거
//  WiFi.disconnect();
//  delay(1000);
//
//  // -----------------------------
//  // 1. 주변 Wi-Fi 검색
//  // -----------------------------
//
//  Serial.println("Scanning WiFi...");
//
//  int n = WiFi.scanNetworks();
//
//  Serial.print("Networks found: ");
//  Serial.println(n);
//
//  for (int i = 0; i < n; i++) {
//
//    Serial.print(i + 1);
//    Serial.print(". ");
//
//    Serial.print(WiFi.SSID(i));
//
//    Serial.print(" | RSSI: ");
//    Serial.print(WiFi.RSSI(i));
//
//    Serial.print(" | Channel: ");
//    Serial.print(WiFi.channel(i));
//
//    Serial.print(" | Encryption: ");
//    Serial.println(WiFi.encryptionType(i));
//  }
//
//  Serial.println();
//  Serial.println("=============================");
//  Serial.println("Connecting to kenta...");
//
//  // -----------------------------
//  // 2. 핫스팟 연결
//  // -----------------------------
//
//  WiFi.begin(ssid, password);
//
//  unsigned long startTime = millis();
//
//  while (
//    WiFi.status() != WL_CONNECTED &&
//    millis() - startTime < 30000
//  ) {
//
//    Serial.print("status = ");
//    Serial.println(WiFi.status());
//
//    delay(1000);
//  }
//  Serial.print("IP Address: ");
//
//Serial.println(WiFi.localIP());
//
//  // -----------------------------
//  // 3. 결과
//  // -----------------------------
//
//  Serial.println();
//
//  if (WiFi.status() == WL_CONNECTED) {
//
//    Serial.println("===== CONNECTED =====");
//
//    Serial.print("SSID: ");
//    Serial.println(WiFi.SSID());
//
//    Serial.print("IP: ");
//    Serial.println(WiFi.localIP());
//
//    Serial.print("Gateway: ");
//    Serial.println(WiFi.gatewayIP());
//
//    Serial.print("RSSI: ");
//    Serial.println(WiFi.RSSI());
//
//  } else {
//
//    Serial.println("===== CONNECTION FAILED =====");
//
//    Serial.print("Final status: ");
//    Serial.println(WiFi.status());
//  }
//}
//
//void loop() {
//
//}
