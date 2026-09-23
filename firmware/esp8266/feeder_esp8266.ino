#include <ESP8266WiFi.h>
#include <ESP8266WiFiMulti.h>
#include <ESP8266WebServer.h>

ESP8266WiFiMulti wifiMulti;
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

int currentLevel = 50;


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

  Serial.println("START");

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

  Serial.println("STOP");

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

  Serial.println("FORWARD");

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

  Serial.println("REVERSE");

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
    "\"connected\":true,"
    "\"speed\":" + String(currentLevel) +
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


  // HTTP API 등록

  server.on("/", handleRoot);
  server.on("/start", handleStart);
  server.on("/stop", handleStop);
  server.on("/forward", handleForward);
  server.on("/reverse", handleReverse);
  server.on("/speed", handleSpeed);
  server.on("/status", handleStatus);


  server.begin();
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
}
