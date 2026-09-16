#include <Servo.h>
#include <SoftwareSerial.h>

Servo myservo;

const int INIT_POS = 70;
const int OPEN_POS = 160;
const int SERVO_PIN = A5;

#define FL_R A0
#define FL_L A1
#define BL_R A2
#define BL_L A3

const int B1A = 3;
const int B1B = 5;
const int A1A = 6;
const int A1B = 11;

const int BLACK = 1;
const int WHITE = 0;

// Arduino D12 = RX <- ESP TX
// Arduino D13 = TX -> ESP RX (3.3V level conversion recommended)
SoftwareSerial espSerial(12, 13);

enum AgvState {
  IDLE,
  FORWARD_RUN,
  BOX_OPENING,
  BOX_WAIT,
  BOX_CLOSING,
  RETURN_RUN,
  STOPPED
};

AgvState state = IDLE;

int motor_speed = 110;          // actual PWM: 75~255
int speed_level = 50;           // web: 1~100
const long FORWARD_TICKS = 400;
const long RETURN_TICKS = 600;  // original movetime * 1.5
long motionTicks = 0;

int servoPos = INIT_POS;
unsigned long servoTimer = 0;
unsigned long stateTimer = 0;

void setMotorSpeedFromLevel(int level) {
  speed_level = constrain(level, 1, 100);
  motor_speed = map(speed_level, 1, 100, 75, 255);
}

void forwardMotor() {
  analogWrite(A1B, 0);
  analogWrite(A1A, motor_speed);
  analogWrite(B1B, motor_speed);
  analogWrite(B1A, 0);
}

void backwardMotor() {
  analogWrite(A1B, motor_speed);
  analogWrite(A1A, 0);
  analogWrite(B1B, 0);
  analogWrite(B1A, motor_speed);
}

void stopMotor() {
  analogWrite(A1B, 0);
  analogWrite(A1A, 0);
  analogWrite(B1B, 0);
  analogWrite(B1A, 0);
}

void cw() {
  analogWrite(A1B, 0);
  analogWrite(A1A, 0);
  analogWrite(B1B, motor_speed);
  analogWrite(B1A, 0);
}

void ccw() {
  analogWrite(A1B, 0);
  analogWrite(A1A, motor_speed);
  analogWrite(B1B, 0);
  analogWrite(B1A, 0);
}

void lineForward() {
  int F_Left = digitalRead(FL_L);
  int F_Right = digitalRead(FL_R);

  if (F_Right == BLACK && F_Left == BLACK) forwardMotor();
  else if (F_Right == WHITE && F_Left == BLACK) ccw();
  else if (F_Right == BLACK && F_Left == WHITE) cw();
  else stopMotor();
}

void lineBackward() {
  int B_Left = digitalRead(BL_L);
  int B_Right = digitalRead(BL_R);

  if (B_Right == BLACK && B_Left == BLACK) backwardMotor();
  else if (B_Right == WHITE && B_Left == BLACK) cw();
  else if (B_Right == BLACK && B_Left == WHITE) ccw();
  else stopMotor();
}

void beginMission() {
  motionTicks = 0;
  state = FORWARD_RUN;
}

void beginReturn() {
  stopMotor();
  motionTicks = 0;
  state = RETURN_RUN;
}

void beginBox() {
  stopMotor();
  servoPos = INIT_POS;
  myservo.write(servoPos);
  servoTimer = millis();
  state = BOX_OPENING;
}

void processCommand(String command) {
  command.trim();

  if (command == "START") {
    beginMission();
    Serial.println("AGV START");
  }
  else if (command == "STOP") {
    stopMotor();
    state = STOPPED;
    Serial.println("AGV STOP");
  }
  else if (command == "RETURN") {
    beginReturn();
    Serial.println("AGV RETURN");
  }
  else if (command == "BOX") {
    beginBox();
    Serial.println("AGV BOX");
  }
  else if (command.startsWith("S:")) {
    int value = command.substring(2).toInt();
    setMotorSpeedFromLevel(value);
    Serial.print("AGV SPEED ");
    Serial.println(motor_speed);
  }
}

void checkEsp() {
  while (espSerial.available()) {
    String command = espSerial.readStringUntil('\n');
    processCommand(command);
  }
}

void updateServoBox() {
  unsigned long now = millis();

  if (state == BOX_OPENING) {
    if (now - servoTimer >= 15) {
      servoTimer = now;
      if (servoPos < OPEN_POS) {
        servoPos++;
        myservo.write(servoPos);
      } else {
        stateTimer = now;
        state = BOX_WAIT;
      }
    }
  }
  else if (state == BOX_WAIT) {
    if (now - stateTimer >= 1000) {
      state = BOX_CLOSING;
      servoTimer = now;
    }
  }
  else if (state == BOX_CLOSING) {
    if (now - servoTimer >= 15) {
      servoTimer = now;
      if (servoPos > INIT_POS) {
        servoPos--;
        myservo.write(servoPos);
      } else {
        motionTicks = 0;
        state = RETURN_RUN;
      }
    }
  }
}

void setup() {
  Serial.begin(9600);
  espSerial.begin(9600);
  espSerial.setTimeout(20);

  myservo.attach(SERVO_PIN);
  myservo.write(INIT_POS);

  pinMode(FL_R, INPUT);
  pinMode(FL_L, INPUT);
  pinMode(BL_R, INPUT);
  pinMode(BL_L, INPUT);

  pinMode(A1B, OUTPUT);
  pinMode(A1A, OUTPUT);
  pinMode(B1B, OUTPUT);
  pinMode(B1A, OUTPUT);

  stopMotor();
  setMotorSpeedFromLevel(50);
  Serial.println("AGV Ready");
}

void loop() {
  checkEsp();

  switch (state) {
    case FORWARD_RUN:
      lineForward();
      motionTicks++;
      if (motionTicks >= FORWARD_TICKS) {
        stopMotor();
        beginBox();
      }
      delay(15);
      break;

    case BOX_OPENING:
    case BOX_WAIT:
    case BOX_CLOSING:
      updateServoBox();
      break;

    case RETURN_RUN:
      lineBackward();
      motionTicks++;
      if (motionTicks >= RETURN_TICKS) {
        stopMotor();
        state = IDLE;
        Serial.println("AGV CYCLE COMPLETE");
      }
      delay(15);
      break;

    case IDLE:
    case STOPPED:
    default:
      stopMotor();
      delay(5);
      break;
  }
}
