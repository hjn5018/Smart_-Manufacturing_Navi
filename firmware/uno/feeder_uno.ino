#include <Stepper.h>
#include <SoftwareSerial.h>

// ======================================================
// Stepper Motor
// ======================================================

#define STEPS 2048

#define IN1 11
#define IN2 10
#define IN3 9
#define IN4 8

Stepper feederMotor(
  STEPS,
  IN1,
  IN3,
  IN2,
  IN4
);


// ======================================================
// ESP-01 Serial
//
// Arduino D12 = RX ← ESP TX
// Arduino D13 = TX → ESP RX
// ======================================================

SoftwareSerial espSerial(12, 13);


// ======================================================
// Feeder State
// ======================================================

bool isRunning = false;

// 1 = Forward
// -1 = Reverse
int direction = 1;

// RPM
int motorSpeed = 8;


// ======================================================
// MOTOR RELEASE
// ======================================================

void releaseMotor() {

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}


// ======================================================
// COMMAND PROCESSING
// ======================================================

void processCommand(String command) {

  command.trim();


  // START
  if (command == "START") {

    isRunning = true;

    Serial.println("Feeder START");
  }


  // STOP
  else if (command == "STOP") {

    isRunning = false;

    releaseMotor();

    Serial.println("Feeder STOP");
  }


  // FORWARD
  else if (command == "FORWARD") {

    direction = 1;

    Serial.println("Direction FORWARD");
  }


  // REVERSE
  else if (command == "REVERSE") {

    direction = -1;

    Serial.println("Direction REVERSE");
  }


  // SPEED
  else if (command.startsWith("S:")) {

    int speedValue =
      command.substring(2).toInt();

    speedValue = constrain(
      speedValue,
      1,
      15
    );

    motorSpeed = speedValue;

    feederMotor.setSpeed(
      motorSpeed
    );

    Serial.print("Speed: ");
    Serial.print(motorSpeed);
    Serial.println(" RPM");
  }
}


// ======================================================
// SETUP
// ======================================================

void setup() {

  // PC Serial Monitor
  Serial.begin(9600);


  // ESP communication
  espSerial.begin(9600);


  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);


  feederMotor.setSpeed(
    motorSpeed
  );


  releaseMotor();


  Serial.println("Feeder Ready");
}


// ======================================================
// LOOP
// ======================================================

void loop() {

  // ESP 명령 수신
  if (espSerial.available()) {

    String command =
      espSerial.readStringUntil('\n');

    processCommand(command);
  }


  // Motor Running
  if (isRunning) {

    feederMotor.step(
      direction * 8
    );
  }
}
