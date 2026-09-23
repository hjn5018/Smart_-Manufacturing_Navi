#include <Servo.h>
#include <SoftwareSerial.h>

// ======================================================
// Servo
// ======================================================

Servo sortingM;


// ======================================================
// Color Sensor
// ======================================================

#define S0 A1
#define S1 A2
#define S2 A3
#define S3 A4

#define sensorOut A0
#define LED A5

int frequency = 0;
int getcolor = 0;


// ======================================================
// Stepper Driver
// ======================================================

const int stepPin = 8;
const int dirPin  = 9;
const int EN      = 10;


// ======================================================
// IR Sensor
// ======================================================

const int IRsensor = 11;


// ======================================================
// ESP-01 Communication
//
// Arduino D12 = RX ← ESP TX
// Arduino D13 = TX → ESP RX
//
// SoftwareSerial(RX, TX)
// ======================================================

SoftwareSerial espSerial(12, 13);


// ======================================================
// ESP Wi-Fi State
// ======================================================

bool espWifiConnected = false;

String espIPAddress = "UNKNOWN";


// ======================================================
// Conveyor State
// ======================================================

bool isRunning = false;

// true  = Forward
// false = Reverse
bool forwardDirection = true;


// ======================================================
// Speed
// ======================================================

// Web speed 1 ~ 100
int speedLevel = 50;

// 작은 숫자 = 빠름
// 큰 숫자 = 느림
int motorDelay = 1200;


// ======================================================
// Sorting Color
//
// 2 = RED
// 3 = BLUE
// ======================================================

int targetColor = 2;


// ======================================================
// Function Prototypes
// ======================================================

void checkESPCommand();
void processCommand(String command);
void updateDirection();
void stepMotorOnce();
void moveSteps(int steps);
int readColor();


// ======================================================
// Update Direction
// ======================================================

void updateDirection() {

  if (forwardDirection) {

    digitalWrite(dirPin, LOW);

  } else {

    digitalWrite(dirPin, HIGH);
  }
}


// ======================================================
// Motor Pulse
// ======================================================

void stepMotorOnce() {

  digitalWrite(stepPin, HIGH);

  delayMicroseconds(motorDelay);

  digitalWrite(stepPin, LOW);

  delayMicroseconds(motorDelay);
}


// ======================================================
// Move Steps
// ======================================================

void moveSteps(int steps) {

  for (int i = 0; i < steps; i++) {

    // 이동 중에도 ESP 명령 확인
    checkESPCommand();

    if (!isRunning) {
      return;
    }

    stepMotorOnce();
  }
}


// ======================================================
// ESP COMMAND PROCESS
// ======================================================

void processCommand(String command) {

  command.trim();

  // 빈 문자열 무시
  if (command.length() == 0) {
    return;
  }


  // ====================================================
  // Wi-Fi Connected
  // ESP → WIFI:CONNECTED
  // ====================================================

  if (command == "WIFI:CONNECTED") {

    espWifiConnected = true;

    Serial.println();
    Serial.println("================================");
    Serial.println("[ESP] WiFi CONNECTED");
    Serial.println("================================");
  }


  // ====================================================
  // Wi-Fi Disconnected
  // ESP → WIFI:DISCONNECTED
  // ====================================================

  else if (command == "WIFI:DISCONNECTED") {

    espWifiConnected = false;

    espIPAddress = "UNKNOWN";

    Serial.println();
    Serial.println("================================");
    Serial.println("[ESP] WiFi DISCONNECTED");
    Serial.println("================================");
  }


  // ====================================================
  // IP Address
  // ESP → IP:172.20.10.2
  // ====================================================

  else if (command.startsWith("IP:")) {

    espIPAddress = command.substring(3);

    Serial.println();
    Serial.println("================================");

    Serial.print("[ESP] IP Address: ");
    Serial.println(espIPAddress);

    Serial.println("================================");
  }


  // ====================================================
  // START
  // ====================================================

  else if (command == "START") {

    isRunning = true;

    digitalWrite(
      EN,
      LOW
    );

    Serial.println("[ESP CMD] Conveyor START");
  }


  // ====================================================
  // STOP
  // ====================================================

  else if (command == "STOP") {

    isRunning = false;

    // Stepper Driver Disable
    digitalWrite(
      EN,
      HIGH
    );

    Serial.println("[ESP CMD] Conveyor STOP");
  }


  // ====================================================
  // FORWARD
  // ====================================================

  else if (command == "FORWARD") {

    forwardDirection = true;

    updateDirection();

    Serial.println("[ESP CMD] Direction FORWARD");
  }


  // ====================================================
  // REVERSE
  // ====================================================

  else if (command == "REVERSE") {

    forwardDirection = false;

    updateDirection();

    Serial.println("[ESP CMD] Direction REVERSE");
  }


  // ====================================================
  // SPEED
  //
  // ESP → S:1 ~ S:100
  // ====================================================

  else if (command.startsWith("S:")) {

    int value =
      command.substring(2).toInt();

    value =
      constrain(
        value,
        1,
        100
      );

    speedLevel = value;


    // 1   = 느림
    // 100 = 빠름
    //
    // 2000us ~ 500us

    motorDelay =
      map(
        speedLevel,
        1,
        100,
        2000,
        500
      );


    Serial.print("[ESP CMD] Speed Level: ");
    Serial.println(speedLevel);

    Serial.print("[ESP CMD] Motor Delay: ");
    Serial.print(motorDelay);
    Serial.println(" us");
  }


  // ====================================================
  // SORT RED
  // ====================================================

  else if (command == "COLOR:RED") {

    targetColor = 2;

    Serial.println("[ESP CMD] Sorting Color RED");
  }


  // ====================================================
  // SORT BLUE
  // ====================================================

  else if (command == "COLOR:BLUE") {

    targetColor = 3;

    Serial.println("[ESP CMD] Sorting Color BLUE");
  }


  // ====================================================
  // Unknown message
  //
  // ESP에서 예상하지 못한 문자열이 들어오더라도
  // 버리지 않고 Serial Monitor에 표시
  // ====================================================

  else {

    Serial.print("[ESP RAW] ");
    Serial.println(command);
  }
}


// ======================================================
// Check ESP Command
// ======================================================

void checkESPCommand() {

  while (espSerial.available()) {

    String command =
      espSerial.readStringUntil('\n');

    processCommand(command);
  }
}


// ======================================================
// SETUP
// ======================================================

void setup() {

  // ====================================================
  // PC Serial Monitor
  // ====================================================

  Serial.begin(9600);


  // ====================================================
  // ESP-01 UART
  // ESP 코드의 Serial.begin(9600)과 동일해야 함
  // ====================================================

  espSerial.begin(9600);

  // UART read timeout 단축
  espSerial.setTimeout(50);


  // ====================================================
  // Color Sensor
  // ====================================================

  pinMode(S0, OUTPUT);
  pinMode(S1, OUTPUT);
  pinMode(S2, OUTPUT);
  pinMode(S3, OUTPUT);

  pinMode(
    sensorOut,
    INPUT
  );

  pinMode(
    LED,
    OUTPUT
  );


  digitalWrite(
    LED,
    HIGH
  );


  // TCS3200 frequency scaling
  digitalWrite(
    S0,
    HIGH
  );

  digitalWrite(
    S1,
    LOW
  );


  // ====================================================
  // Stepper
  // ====================================================

  pinMode(
    EN,
    OUTPUT
  );

  pinMode(
    dirPin,
    OUTPUT
  );

  pinMode(
    stepPin,
    OUTPUT
  );


  // 처음에는 정지
  digitalWrite(
    EN,
    HIGH
  );

  updateDirection();


  // ====================================================
  // Servo
  // ====================================================

  sortingM.attach(5);

  sortingM.write(0);


  // ====================================================
  // IR Sensor
  // ====================================================

  pinMode(
    IRsensor,
    INPUT_PULLUP
  );


  // ====================================================
  // Startup Message
  // ====================================================

  Serial.println();
  Serial.println("================================");
  Serial.println("Color Sorting Conveyor Ready");
  Serial.println("Waiting for ESP-01...");
  Serial.println("================================");
}


// ======================================================
// LOOP
// ======================================================

void loop() {

  // ====================================================
  // ESP 명령 확인
  // ====================================================

  checkESPCommand();


  // ====================================================
  // STOP 상태
  // ====================================================

  if (!isRunning) {

    delay(5);

    return;
  }


  // ====================================================
  // Conveyor movement
  // ====================================================

  digitalWrite(
    EN,
    LOW
  );

  updateDirection();


  // ====================================================
  // IR 센서 위치에서 조금 벗어나기
  // ====================================================

  moveSteps(100);


  if (!isRunning) {
    return;
  }


  // ====================================================
  // 다음 턱까지 이동
  // ====================================================

  for (int i = 0; i < 500; i++) {

    checkESPCommand();

    if (!isRunning) {
      return;
    }


    if (
      digitalRead(IRsensor) == LOW
    ) {

      break;
    }


    stepMotorOnce();
  }


  if (!isRunning) {
    return;
  }


  delay(1);


  // ====================================================
  // Color Detection
  // ====================================================

  getcolor = readColor();


  // ====================================================
  // Target Color
  // ====================================================

  if (getcolor == targetColor) {

    Serial.println("Target Color Detected");


    // ==================================================
    // 분류 위치까지 이동
    // ==================================================

    moveSteps(595);


    if (!isRunning) {
      return;
    }


    // ==================================================
    // IR 센서까지 추가 이동
    // ==================================================

    for (int i = 0; i < 300; i++) {

      checkESPCommand();

      if (!isRunning) {
        return;
      }


      if (
        digitalRead(IRsensor) == LOW
      ) {

        break;
      }


      stepMotorOnce();
    }


    if (!isRunning) {
      return;
    }


    delay(500);


    // ==================================================
    // Servo Sorting
    // ==================================================

    for (int i = 0; i <= 180; i++) {

      sortingM.write(i);

      delay(3);

      // Servo 움직이는 동안에도 STOP 수신
      checkESPCommand();

      if (!isRunning) {

        digitalWrite(EN, HIGH);

        return;
      }
    }


    delay(500);


    // ==================================================
    // Servo Return
    // ==================================================

    for (int i = 180; i >= 0; i--) {

      sortingM.write(i);

      delay(3);

      checkESPCommand();

      if (!isRunning) {

        digitalWrite(EN, HIGH);

        return;
      }
    }


    delay(500);
  }


  // ====================================================
  // Empty Belt
  // ====================================================

  else if (getcolor == 1) {

    Serial.println("Empty Belt");
  }


  // ====================================================
  // Other Color
  // ====================================================

  else {

    Serial.println("PASS");
  }


  getcolor = 0;
}


// ======================================================
// READ COLOR
// ======================================================

int readColor() {

  digitalWrite(
    LED,
    HIGH
  );


  // ====================================================
  // RED
  // ====================================================

  long R = 0;

  digitalWrite(
    S2,
    LOW
  );

  digitalWrite(
    S3,
    LOW
  );


  for (int i = 0; i < 100; i++) {

    frequency =
      pulseIn(
        sensorOut,
        LOW
      );

    R += frequency;

    delayMicroseconds(50);
  }


  int Ra = R / 100;


  // ====================================================
  // GREEN
  // ====================================================

  long G = 0;

  digitalWrite(
    S2,
    HIGH
  );

  digitalWrite(
    S3,
    HIGH
  );


  for (int i = 0; i < 100; i++) {

    frequency =
      pulseIn(
        sensorOut,
        LOW
      );

    G += frequency;

    delayMicroseconds(50);
  }


  int Ga = G / 100;


  // ====================================================
  // BLUE
  // ====================================================

  long B = 0;

  digitalWrite(
    S2,
    LOW
  );

  digitalWrite(
    S3,
    HIGH
  );


  for (int i = 0; i < 100; i++) {

    frequency =
      pulseIn(
        sensorOut,
        LOW
      );

    B += frequency;

    delayMicroseconds(50);
  }


  int Ba = B / 100;


  // ====================================================
  // CLEAR
  // ====================================================

  long C = 0;

  digitalWrite(
    S2,
    HIGH
  );

  digitalWrite(
    S3,
    LOW
  );


  for (int i = 0; i < 100; i++) {

    frequency =
      pulseIn(
        sensorOut,
        LOW
      );

    C += frequency;

    delayMicroseconds(50);
  }


  int Ca = C / 100;


  // ====================================================
  // Debug
  // ====================================================

  Serial.print("R: ");
  Serial.print(Ra);

  Serial.print(" G: ");
  Serial.print(Ga);

  Serial.print(" B: ");
  Serial.print(Ba);

  Serial.print(" C: ");
  Serial.println(Ca);


  // ====================================================
  // RED
  // ====================================================

  if (
    Ra < 150 &&
    Ga > 180 &&
    Ba > 170 &&
    Ra < Ba &&
    Ra < Ga
  ) {

    Serial.println("Detected RED");

    digitalWrite(
      LED,
      LOW
    );

    return 2;
  }


  // ====================================================
  // BLUE
  // ====================================================

  else if (
    Ba < 180 &&
    Ba < Ra &&
    Ba < Ga &&
    (Ra - Ba) > 25 &&
    (Ga - Ba) > 25
  ) {

    Serial.println("Detected BLUE");

    digitalWrite(
      LED,
      LOW
    );

    return 3;
  }


  // ====================================================
  // EMPTY BELT
  // ====================================================

  else if (
    Ra > 220 &&
    Ga > 250 &&
    Ba > 220 &&
    Ca > 80
  ) {

    Serial.println("Detected BELT");

    digitalWrite(
      LED,
      LOW
    );e

    return 1;
  }


  // ====================================================
  // UNKNOWN
  // ====================================================

  else {

    Serial.println("Unknown Color");

    digitalWrite(
      LED,
      LOW
    );

    return 4;
  }
}
