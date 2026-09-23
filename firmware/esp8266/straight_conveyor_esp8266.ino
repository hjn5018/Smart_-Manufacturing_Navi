#include <ESP8266WiFi.h>
#include <ESP8266WiFiMulti.h>
#include <ESP8266WebServer.h>
#include <WebSocketsClient.h>

ESP8266WiFiMulti wifiMulti;

// Wi-Fi Candidates (2개의 후보 중 연결 가능한 AP 자동 접속)
const char* WIFI_SSID_1 = "kenta";
const char* WIFI_PASSWORD_1 = "00001111";
const char* SERVER_HOST_1 = "172.20.10.13";

const char* WIFI_SSID_2 = "LLim";
const char* WIFI_PASSWORD_2 = "limche123";
const char* SERVER_HOST_2 = "172.21.134.80";

const char* SERVER_HOST = SERVER_HOST_1;
String serverHost = SERVER_HOST_1;
const uint16_t SERVER_PORT = 8000;
const char* PROVISIONING_KEY = "planner-device-provisioning-key";
const char* CONTROL_KEY = "planner-device-control-key";
const char* DEVICE_TYPE = "STRAIGHT_CONVEYOR";
const char* FIRMWARE_VERSION = "1.0.0";

WebSocketsClient provisioningWs;
WebSocketsClient controlWs;
ESP8266WebServer server(80);

String deviceId;
bool provisioningComplete = false;
bool startControlRequested = false;
bool controlStarted = false;
bool controlReady = false;

bool running = false;
bool emergencyStopped = false;
int currentSpeed = 50;       // Operator-facing level: 1 to 100
String currentDirection = "FORWARD";

unsigned long heartbeatIntervalMs = 15000;
unsigned long lastHeartbeatMs = 0;

// The Uno command sketch must ignore lines starting with DBG:.
void debugLog(const String& message) {
  Serial.print("DBG:");
  Serial.println(message);
}

String makeDeviceId(String mac) {
  mac.replace(":", "");
  mac.toLowerCase();
  return "esp8266-" + mac;
}

// The attached Arduino firmware expects S:<delay>, not S:<level>.
int speedToMotorDelay(int level) {
  level = constrain(level, 1, 100);
  return map(level, 1, 100, 3000, 200);
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

void sendUnoCommand(const String& command) {
  // ESP TX -> Arduino RX. Keep this stream to command lines only.
  Serial.println(command);
  debugLog("UNO_CMD=" + command);
}

void addCorsHeader() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
}

void sendHttpText(int code, const String& text) {
  addCorsHeader();
  server.send(code, "text/plain", text);
}

void sendAck(const String& commandId) {
  if (!controlReady || commandId.length() == 0) return;
  // Older arduinoWebSockets versions accept String& only, not a temporary.
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
    sendUnoCommand("EMERGENCY_STOP");
    sendResult(commandId);
    sendStatus();
    return;
  }

  if (command == "RELEASE_EMERGENCY_STOP") {
    sendAck(commandId);
    emergencyStopped = false;
    running = false;
    sendUnoCommand("RELEASE_EMERGENCY_STOP");
    sendResult(commandId);
    sendStatus();
    return;
  }

  if (emergencyStopped) {
    sendError(commandId, "device is emergency stopped");
    return;
  }

  if (command == "START" || command == "FORWARD") {
    sendAck(commandId);
    running = true;
    currentDirection = "FORWARD";
    // Existing Arduino code understands START.
    sendUnoCommand("START");
  } else if (command == "REVERSE") {
    sendAck(commandId);
    running = true;
    currentDirection = "REVERSE";
    // Requires a matching REVERSE handler in the Arduino motor sketch.
    sendUnoCommand("REVERSE");
  } else if (command == "STOP") {
    sendAck(commandId);
    running = false;
    sendUnoCommand("STOP");
  } else if (command == "SET_SPEED") {
    int speed = getJsonInt(message, "speed", -1);
    if (speed < 1 || speed > 100) {
      sendError(commandId, "SET_SPEED requires an integer between 1 and 100");
      return;
    }
    sendAck(commandId);
    currentSpeed = speed;
    sendUnoCommand("S:" + String(speedToMotorDelay(speed)));
  } else if (command == "RESET") {
    sendAck(commandId);
    running = false;
    emergencyStopped = false;
    currentDirection = "FORWARD";
    sendUnoCommand("RESET");
  } else if (command == "STATUS_SYNC") {
    sendAck(commandId);
  } else {
    sendError(commandId, "unsupported command: " + command);
    return;
  }

  sendResult(commandId);
  sendStatus();
}

// ======================================================
// Optional local HTTP compatibility for the existing React device cards.
// Planner/Tool calling still uses the WebSocket handlers above.
// ======================================================

void handleHttpStart() {
  if (emergencyStopped) {
    sendHttpText(409, "device is emergency stopped");
    return;
  }
  running = true;
  currentDirection = "FORWARD";
  sendUnoCommand("START");
  sendStatus();
  sendHttpText(200, "START");
}

void handleHttpStop() {
  running = false;
  sendUnoCommand("STOP");
  sendStatus();
  sendHttpText(200, "STOP");
}

void handleHttpReverse() {
  if (emergencyStopped) {
    sendHttpText(409, "device is emergency stopped");
    return;
  }
  running = true;
  currentDirection = "REVERSE";
  sendUnoCommand("REVERSE");
  sendStatus();
  sendHttpText(200, "REVERSE");
}

void handleHttpSpeed() {
  if (!server.hasArg("value")) {
    sendHttpText(400, "Missing value");
    return;
  }
  int speed = server.arg("value").toInt();
  if (speed < 1 || speed > 100) {
    sendHttpText(400, "Speed must be between 1 and 100");
    return;
  }
  currentSpeed = speed;
  sendUnoCommand("S:" + String(speedToMotorDelay(speed)));
  sendStatus();
  sendHttpText(200, String(speed));
}

void handleHttpStatus() {
  addCorsHeader();
  String json = "{\"connected\":" + String(controlReady ? "true" : "false");
  json += ",\"running\":" + String(running ? "true" : "false");
  json += ",\"speed\":" + String(currentSpeed);
  json += ",\"direction\":\"" + currentDirection + "\"}";
  server.send(200, "application/json", json);
}

void registerHttpRoutes() {
  server.on("/start", handleHttpStart);
  server.on("/forward", handleHttpStart);
  server.on("/stop", handleHttpStop);
  server.on("/reverse", handleHttpReverse);
  server.on("/speed", handleHttpSpeed);
  server.on("/status", handleHttpStatus);
  server.begin();
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

void setup() {
  // ESP TX is connected to Uno RX. The Uno sketch ignores DBG: lines.
  Serial.begin(9600);
  delay(300);
  debugLog("ESP_BOOT");
  WiFi.mode(WIFI_STA);
  wifiMulti.addAP(WIFI_SSID_1, WIFI_PASSWORD_1);
  wifiMulti.addAP(WIFI_SSID_2, WIFI_PASSWORD_2);
  debugLog("WIFI_CONNECTING");
  while (wifiMulti.run() != WL_CONNECTED) delay(500);
  deviceId = makeDeviceId(WiFi.macAddress());
  String localIp = WiFi.localIP().toString();
  if (WiFi.SSID() == WIFI_SSID_2) {
    serverHost = SERVER_HOST_2;
  } else {
    serverHost = SERVER_HOST_1;
  }
  debugLog("WIFI_CONNECTED");
  debugLog("WIFI_SSID=" + WiFi.SSID());
  debugLog("WIFI_IP=" + localIp);
  debugLog("DEVICE_ID=" + deviceId);
  debugLog("SERVER_HOST=" + serverHost);
  registerHttpRoutes();
  startProvisioning();
}

void loop() {
  server.handleClient();
  if (wifiMulti.run() != WL_CONNECTED) {
    delay(10);
    return;
  }
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
