#include <SoftwareSerial.h>

// ======================================================
// Stepper driver pins
// ======================================================

#define STEP 2
#define DIR 5
#define EN 8

// Driver enable polarity. Change these two values together if your
// stepper driver is enabled when EN is HIGH.
const int DRIVER_ENABLED = LOW;
const int DRIVER_DISABLED = HIGH;

// Change these two values together if the conveyor direction is reversed.
const int FORWARD_DIRECTION = HIGH;
const int REVERSE_DIRECTION = LOW;

// ======================================================
// ESP8266 serial wiring
//
// ESP TX / GPIO1 -> Uno D10
// Uno D9 -> ESP RX / GPIO3 through a 5V-to-3.3V level shifter (optional)
// ESP GND <-> Uno GND
// ======================================================

SoftwareSerial espSerial(10, 9); // RX, TX
String commandBuffer = "";

bool running = false;
bool emergencyStopped = false;

// The ESP sends S:<delay>. Smaller microsecond delays mean faster motion.
int stepDelayUs = 900;

void stopMotor() {
  running = false;
  digitalWrite(STEP, LOW);
  digitalWrite(EN, DRIVER_DISABLED);
}

void startMotor() {
  if (emergencyStopped) return;
  digitalWrite(EN, DRIVER_ENABLED);
  running = true;
}

void setDirection(int direction) {
  digitalWrite(DIR, direction);
}

void setSpeedDelay(int value) {
  // Matches the ESP mapping: S:3000 is slow, S:200 is fast.
  stepDelayUs = constrain(value, 200, 3000);
}

void processCommand(String command) {
  command.trim();
  if (command.length() == 0) return;

  // This line is displayed on the Uno USB Serial Monitor.
  Serial.print("[UNO RX] ");
  Serial.println(command);

  // ESP connection diagnostics do not operate the motor.
  if (command.startsWith("DBG:")) return;

  if (command == "EMERGENCY_STOP") {
    emergencyStopped = true;
    stopMotor();
    Serial.println("[UNO] EMERGENCY STOP LATCHED");
    return;
  }

  if (command == "RELEASE_EMERGENCY_STOP") {
    emergencyStopped = false;
    stopMotor();
    Serial.println("[UNO] EMERGENCY STOP RELEASED");
    return;
  }

  // Reject every motion command until the emergency stop is explicitly released.
  if (emergencyStopped) {
    Serial.println("[UNO] COMMAND IGNORED: EMERGENCY STOP LATCHED");
    return;
  }

  if (command == "START" || command == "FORWARD") {
    setDirection(FORWARD_DIRECTION);
    startMotor();
    Serial.println("[UNO] FORWARD START");
    return;
  }

  if (command == "REVERSE") {
    setDirection(REVERSE_DIRECTION);
    startMotor();
    Serial.println("[UNO] REVERSE START");
    return;
  }

  if (command == "STOP") {
    stopMotor();
    Serial.println("[UNO] STOP");
    return;
  }

  if (command == "RESET") {
    emergencyStopped = false;
    stopMotor();
    setDirection(FORWARD_DIRECTION);
    Serial.println("[UNO] RESET");
    return;
  }

  if (command.startsWith("S:")) {
    setSpeedDelay(command.substring(2).toInt());
    Serial.print("[UNO] STEP DELAY US = ");
    Serial.println(stepDelayUs);
    return;
  }

  Serial.println("[UNO] UNKNOWN COMMAND");
}

void readEspCommands() {
  while (espSerial.available() > 0) {
    char received = espSerial.read();

    if (received == '\n') {
      processCommand(commandBuffer);
      commandBuffer = "";
    } else if (received != '\r') {
      if (commandBuffer.length() < 64) {
        commandBuffer += received;
      } else {
        commandBuffer = "";
        Serial.println("[UNO] ESP COMMAND BUFFER OVERFLOW");
      }
    }
  }
}

void runOneStep() {
  digitalWrite(STEP, HIGH);
  delayMicroseconds(stepDelayUs);
  digitalWrite(STEP, LOW);
  delayMicroseconds(stepDelayUs);
}

void setup() {
  // USB Serial Monitor only. It does not share the ESP command receiver.
  Serial.begin(9600);
  espSerial.begin(9600);

  pinMode(STEP, OUTPUT);
  pinMode(DIR, OUTPUT);
  pinMode(EN, OUTPUT);

  digitalWrite(STEP, LOW);
  digitalWrite(DIR, FORWARD_DIRECTION);
  digitalWrite(EN, DRIVER_DISABLED);

  Serial.println("[UNO] STRAIGHT CONVEYOR READY");
}

void loop() {
  readEspCommands();

  if (running && !emergencyStopped) {
    runOneStep();
  }
}
