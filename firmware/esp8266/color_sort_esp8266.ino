#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>

ESP8266WebServer server(80);

// ======================================================
// Wi-Fi
// ======================================================

const char* ssid = "LLim";
const char* password = "limche123";

int currentSpeed = 50;
String currentDirection = "FORWARD";
String currentColor = "RED";
bool running = false;


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

  currentDirection = "FORWARD";

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

  currentDirection = "REVERSE";

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

  }

  else if (color == "BLUE") {

    currentColor = "BLUE";

    Serial.println("COLOR:BLUE");

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

  json += "\"connected\":true,";
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

  WiFi.begin(
    ssid,
    password
  );

  while (WiFi.status() != WL_CONNECTED) {

    delay(500);
  }
  Serial.println("WIFI:CONNECTED");
  
  Serial.print("IP:");
  Serial.println(WiFi.localIP());
  
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
}


// ======================================================
// LOOP
// ======================================================

void loop() {

  server.handleClient();
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
