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

const char* WIFI_SSID_2 = "LLim";
const char* WIFI_PASSWORD_2 = "limche123";

// ======================================================
// FastAPI
// ======================================================

const char* SERVER_HOST = "172.20.10.13";
const uint16_t SERVER_PORT = 8000;

const char* PROVISIONING_KEY = "planner-device-provisioning-key";
const char* CONTROL_KEY = "planner-device-control-key";
const char* DEVICE_TYPE = "FEEDER";
const char* FIRMWARE_VERSION = "1.0.0";

String deviceId;
bool provisioningComplete = false;
bool startControlRequested = false;
bool controlStarted = false;
bool controlReady = false;

int currentLevel = 50;
bool running = false;
bool emergencyStopped = false;
String currentDirection = "FORWARD";

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

int levelToRpm(int level) {
  level = constrain(level, 1, 100);
  return map(level, 1, 100, 1, 15);
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
  message += "\"current_speed\":" + String(currentLevel) + ",";
  message += "\"target_speed\":" + String(currentLevel) + ",";
  message += "\"running\":" + String(running ? "true" : "false") + ",";
  message += "\"emergency_stopped\":" + String(emergencyStopped ? "true" : "false");
  message += "}}";
  controlWs.sendTXT(message);
}

void sendResult(const String& commandId) {
  if (!controlReady || commandId.length() == 0) return;
  String message = "{\"type\":\"RESULT\",\"command_id\":\"" + commandId + "\",";
  message += "\"status\":\"COMPLETED\",\"state\":{";
  message += "\"current_speed\":" + String(currentLevel) + ",";
  message += "\"direction\":\"" + currentDirection + "\",";
  message += "\"running\":" + String(running ? "true" : "false") + ",";
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
    currentLevel = speed;
    Serial.println("S:" + String(levelToRpm(currentLevel)));
  } else if (command == "RESET") {
    sendAck(commandId);
    running = false;
    emergencyStopped = false;
    currentDirection = "FORWARD";
    Serial.println("STOP");
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
  provisioningWs.begin(SERVER_HOST, SERVER_PORT, path.c_str());
  provisioningWs.onEvent(provisioningEvent);
  provisioningWs.setReconnectInterval(5000);
}

void startControl() {
  String path = "/ws/boards/" + deviceId + "?control_key=" + String(CONTROL_KEY);
  controlWs.begin(SERVER_HOST, SERVER_PORT, path.c_str());
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

<title>Feeder Control</title>

<style>
body {
    font-family: Arial;
    text-align: center;
    background: #f3f3f3;
    margin-top: 50px;
}

.container {
    background: white;
    width: 360px;
    margin: auto;
    padding: 30px;
    border-radius: 15px;
    box-shadow: 0px 3px 15px #aaa;
}

h1 {
    font-size: 25px;
}

.speed {
    font-size: 40px;
    font-weight: bold;
    margin: 20px;
}

input[type=range] {
    width: 90%;
}

button {
    width: 130px;
    height: 50px;
    margin: 8px;
    border: 0;
    border-radius: 10px;
    font-size: 17px;
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

.status {
    margin-top: 20px;
    font-size: 18px;
}
</style>
</head>

<body>

<div class="container">

<h1>피더 제어</h1>

<div>속도</div>

<div class="speed" id="speedValue">50</div>

<input
type="range"
min="1"
max="100"
value="50"
id="speedSlider"
oninput="changeSpeed(this.value)"
>

<br><br>

<button class="start" onclick="startMotor()">START</button>
<button class="stop" onclick="stopMotor()">STOP</button>

<br>

<button class="direction" onclick="forwardMotor()">FORWARD</button>
<button class="direction" onclick="reverseMotor()">REVERSE</button>

<div class="status" id="status">
상태 : 대기
</div>

<div class="status" id="directionStatus">
방향 : 정방향
</div>

</div>

<script>

let timer;

function changeSpeed(value) {

    document.getElementById("speedValue").innerHTML = value;

    clearTimeout(timer);

    timer = setTimeout(function() {

        fetch("/speed?value=" + value)
        .catch(() => {
            document.getElementById("status").innerHTML =
                "상태 : 통신 오류";
        });

    }, 150);
}

function startMotor() {

    fetch("/start")
    .then(() => {
        document.getElementById("status").innerHTML =
            "상태 : 동작중";
    })
    .catch(() => {
        document.getElementById("status").innerHTML =
            "상태 : 통신 오류";
    });
}

function stopMotor() {

    fetch("/stop")
    .then(() => {
        document.getElementById("status").innerHTML =
            "상태 : 정지";
    })
    .catch(() => {
        document.getElementById("status").innerHTML =
            "상태 : 통신 오류";
    });
}

function forwardMotor() {

    fetch("/forward")
    .then(() => {
        document.getElementById("directionStatus").innerHTML =
            "방향 : 정방향";
    });
}

function reverseMotor() {

    fetch("/reverse")
    .then(() => {
        document.getElementById("directionStatus").innerHTML =
            "방향 : 역방향";
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
  server.sendHeader("Access-Control-Allow-Origin", "*");
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


  int level = server.arg("value").toInt();

  level = constrain(
    level,
    1,
    100
  );

  currentLevel = level;


  // Web UI 1~100
  // Arduino Stepper RPM 1~15

  int rpm = map(
    level,
    1,
    100,
    1,
    15
  );


  // Arduino로 전송
  // 예: S:8

  Serial.print("S:");
  Serial.println(rpm);
  sendStatus();


  addCorsHeader();

  server.send(
    200,
    "text/plain",
    String(rpm)
  );
}


// ======================================================
// STATUS
// ======================================================

void handleStatus() {

  addCorsHeader();

  String json =
    "{"
    "\"connected\":" + String(controlReady ? "true" : "false") + ","
    "\"running\":" + String(running ? "true" : "false") + ","
    "\"speed\":" + String(currentLevel) + ","
    "\"direction\":\"" + currentDirection + "\""
    "}";

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

  // Arduino UNO와 통신
  Serial.begin(9600);

  delay(1000);

  // Wi-Fi 연결
  WiFi.mode(WIFI_STA);
  wifiMulti.addAP(WIFI_SSID_1, WIFI_PASSWORD_1);
  wifiMulti.addAP(WIFI_SSID_2, WIFI_PASSWORD_2);

  while (wifiMulti.run() != WL_CONNECTED) {
    delay(500);
  }
  deviceId = makeDeviceId(WiFi.macAddress());
  String localIp = WiFi.localIP().toString();
  debugLog("WIFI_CONNECTED");
  debugLog("WIFI_SSID=" + WiFi.SSID());
  debugLog("DEVICE_ID=" + deviceId);

  // HTTP API 등록
  server.on("/", handleRoot);
  server.on("/start", handleStart);
  server.on("/stop", handleStop);
  server.on("/forward", handleForward);
  server.on("/reverse", handleReverse);
  server.on("/speed", handleSpeed);
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
