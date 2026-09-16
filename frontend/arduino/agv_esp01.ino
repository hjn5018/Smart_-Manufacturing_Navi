#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>

ESP8266WebServer server(80);

const char* ssid = "kenta";
const char* password = "00001111";

bool running = false;
int currentSpeed = 50;
String currentState = "IDLE";

void cors() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
}

void replyText(const String& text) {
  cors();
  server.send(200, "text/plain", text);
}

void handleRoot() {
  cors();
  server.send(200, "text/html; charset=utf-8",
    "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>AGV Control</title></head><body style='font-family:Arial;text-align:center;padding:30px'>"
    "<h2>AGV Control</h2>"
    "<p><button onclick=\"fetch('/start')\">START</button> <button onclick=\"fetch('/stop')\">STOP</button></p>"
    "<p><button onclick=\"fetch('/return')\">RETURN</button> <button onclick=\"fetch('/box')\">BOX</button></p>"
    "<p>Speed <input type='range' min='1' max='100' value='50' oninput=\"fetch('/speed?value='+this.value)\"></p>"
    "</body></html>"
  );
}

void handleStart() {
  running = true;
  currentState = "MISSION";
  Serial.println("START");
  replyText("START");
}

void handleStop() {
  running = false;
  currentState = "STOPPED";
  Serial.println("STOP");
  replyText("STOP");
}

void handleReturn() {
  running = true;
  currentState = "RETURNING";
  Serial.println("RETURN");
  replyText("RETURN");
}

void handleBox() {
  Serial.println("BOX");
  replyText("BOX");
}

void handleSpeed() {
  if (!server.hasArg("value")) {
    cors();
    server.send(400, "text/plain", "Missing value");
    return;
  }

  int value = constrain(server.arg("value").toInt(), 1, 100);
  currentSpeed = value;

  Serial.print("S:");
  Serial.println(value);
  replyText(String(value));
}

void handleStatus() {
  cors();
  String json = "{";
  json += "\"connected\":true,";
  json += "\"running\":";
  json += running ? "true" : "false";
  json += ",\"speed\":" + String(currentSpeed);
  json += ",\"state\":\"" + currentState + "\"";
  json += "}";
  server.send(200, "application/json", json);
}

void setup() {
  // ESP-01 hardware UART <-> Arduino SoftwareSerial (9600 baud)
  Serial.begin(9600);
  delay(500);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
  }

  server.on("/", handleRoot);
  server.on("/start", handleStart);
  server.on("/stop", handleStop);
  server.on("/return", handleReturn);
  server.on("/box", handleBox);
  server.on("/speed", handleSpeed);
  server.on("/status", handleStatus);
  server.begin();
}

void loop() {
  server.handleClient();
}
