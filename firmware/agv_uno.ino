#include <Servo.h>
#include <SoftwareSerial.h>

Servo myservo;


// ======================================================
// 서보 설정
// ======================================================

const int INIT_POS = 70;
const int OPEN_POS = 160;
const int SERVO_PIN = A5;


// ======================================================
// 라인 센서
// ======================================================

#define FL_R A0
#define FL_L A1
#define BL_R A2
#define BL_L A3


// ======================================================
// 센서 논리값
//
// 검정 = 1
// 흰색 = 0
// ======================================================

const int BLACK = 1;
const int WHITE = 0;


// ======================================================
// 모터 핀
//
// B 모터 = 왼쪽
// A 모터 = 오른쪽
// ======================================================

const int B1A = 3;
const int B1B = 5;

const int A1A = 6;
const int A1B = 11;


// ======================================================
// ESP 통신
//
// Arduino D10 = RX <- ESP TX
// Arduino D9  = TX -> ESP RX
//
// 현재는 ESP -> UNO 위주로 사용
// ======================================================

SoftwareSerial espSerial(10, 9);


// ======================================================
// ESP 수신 버퍼
// ======================================================

String espBuffer = "";


// ======================================================
// 센서 Debug 활성화 여부
//
// true  = 센서값 계속 출력
// false = ESP / 명령 로그만 출력
//
// WebSocket 연결 테스트 중에는 false 추천
// ======================================================

const bool SENSOR_DEBUG = false;


// ======================================================
// AGV 상태
// ======================================================

enum AgvState {

  IDLE,

  FORWARD_RUN,

  BOX_OPENING,
  BOX_WAIT,
  BOX_CLOSING,

  RETURN_RUN,

  STOPPED,
  EMERGENCY_STOPPED
};

AgvState state = IDLE;
bool emergencyStopLatched = false;


// ======================================================
// 모터 속도 설정
// ======================================================

int motor_speed = 120;


// ======================================================
// 좌우 모터 보정
// ======================================================

int LEFT_TRIM  = 0;
int RIGHT_TRIM = 0;


// 라인트레이싱 보정량
const int CORRECTION_AMOUNT = 60;


// 앱 / ESP에서 사용하는 1 ~ 100 속도
int speed_level = 25;


// ======================================================
// 주행 Tick
// ======================================================

const long FORWARD_TICKS = 400;
const long RETURN_TICKS = 600;

long motionTicks = 0;


// ======================================================
// 서보 관련
// ======================================================

int servoPos = INIT_POS;

unsigned long servoTimer = 0;
unsigned long stateTimer = 0;
unsigned long sensorDebugTimer = 0;


// ======================================================
// 실제 좌우 모터 속도 계산
// ======================================================

int getLeftSpeed() {

  return constrain(
    motor_speed + LEFT_TRIM,
    0,
    255
  );
}


int getRightSpeed() {

  return constrain(
    motor_speed + RIGHT_TRIM,
    0,
    255
  );
}


// ======================================================
// 라인트레이싱 보정 속도
// ======================================================

int getLeftCorrectionSpeed() {

  return constrain(
    getLeftSpeed() - CORRECTION_AMOUNT,
    0,
    255
  );
}


int getRightCorrectionSpeed() {

  return constrain(
    getRightSpeed() - CORRECTION_AMOUNT,
    0,
    255
  );
}


// ======================================================
// 속도 단계 설정
//
// ESP:
// S:1 ~ S:100
// ======================================================

void setMotorSpeedFromLevel(int level) {

  speed_level = constrain(
    level,
    1,
    100
  );

  motor_speed = map(
    speed_level,
    1,
    100,
    115,
    210
  );

  Serial.println();

  Serial.print("[UNO] SPEED LEVEL = ");
  Serial.println(speed_level);

  Serial.print("[UNO] BASE PWM = ");
  Serial.println(motor_speed);

  Serial.print("[UNO] LEFT PWM = ");
  Serial.println(getLeftSpeed());

  Serial.print("[UNO] RIGHT PWM = ");
  Serial.println(getRightSpeed());
}


// ======================================================
// 서보 연결
// ======================================================

void servoAttach() {

  if (!myservo.attached()) {

    myservo.attach(SERVO_PIN);
  }
}


// ======================================================
// 서보 해제
// ======================================================

void servoDetach() {

  if (myservo.attached()) {

    myservo.detach();
  }
}


// ======================================================
// 왼쪽 모터
// ======================================================

void leftMotorForward() {

  analogWrite(
    B1A,
    getLeftSpeed()
  );

  analogWrite(
    B1B,
    0
  );
}


void leftMotorBackward() {

  analogWrite(
    B1A,
    0
  );

  analogWrite(
    B1B,
    getLeftSpeed()
  );
}


void leftMotorStop() {

  analogWrite(B1A, 0);
  analogWrite(B1B, 0);
}


// ======================================================
// 오른쪽 모터
// ======================================================

void rightMotorForward() {

  analogWrite(
    A1A,
    getRightSpeed()
  );

  analogWrite(
    A1B,
    0
  );
}


void rightMotorBackward() {

  analogWrite(
    A1A,
    0
  );

  analogWrite(
    A1B,
    getRightSpeed()
  );
}


void rightMotorStop() {

  analogWrite(A1A, 0);
  analogWrite(A1B, 0);
}


// ======================================================
// 직진
// ======================================================

void forwardMotor() {

  leftMotorForward();
  rightMotorForward();
}


// ======================================================
// 후진
// ======================================================

void backwardMotor() {

  leftMotorBackward();
  rightMotorBackward();
}


// ======================================================
// 정지
// ======================================================

void stopMotor() {

  leftMotorStop();
  rightMotorStop();
}


// ======================================================
// 전진 왼쪽 보정
// ======================================================

void forwardCorrectLeft() {

  // 오른쪽 정상
  analogWrite(
    A1A,
    getRightSpeed()
  );

  analogWrite(
    A1B,
    0
  );


  // 왼쪽 감속
  analogWrite(
    B1A,
    getLeftCorrectionSpeed()
  );

  analogWrite(
    B1B,
    0
  );
}


// ======================================================
// 전진 오른쪽 보정
// ======================================================

void forwardCorrectRight() {

  // 오른쪽 감속
  analogWrite(
    A1A,
    getRightCorrectionSpeed()
  );

  analogWrite(
    A1B,
    0
  );


  // 왼쪽 정상
  analogWrite(
    B1A,
    getLeftSpeed()
  );

  analogWrite(
    B1B,
    0
  );
}


// ======================================================
// 후진 왼쪽 보정
// ======================================================

void backwardCorrectLeft() {

  // 오른쪽 정상 후진
  analogWrite(
    A1A,
    0
  );

  analogWrite(
    A1B,
    getRightSpeed()
  );


  // 왼쪽 감속 후진
  analogWrite(
    B1A,
    0
  );

  analogWrite(
    B1B,
    getLeftCorrectionSpeed()
  );
}


// ======================================================
// 후진 오른쪽 보정
// ======================================================

void backwardCorrectRight() {

  // 오른쪽 감속 후진
  analogWrite(
    A1A,
    0
  );

  analogWrite(
    A1B,
    getRightCorrectionSpeed()
  );


  // 왼쪽 정상 후진
  analogWrite(
    B1A,
    0
  );

  analogWrite(
    B1B,
    getLeftSpeed()
  );
}


// ======================================================
// 전진 라인트레이싱
// ======================================================

bool lineForward() {

  int F_Left =
    digitalRead(FL_L);

  int F_Right =
    digitalRead(FL_R);


  // 양쪽 검정 -> 직진

  if (
    F_Left == BLACK &&
    F_Right == BLACK
  ) {

    forwardMotor();

    return true;
  }


  // 왼쪽 검정 / 오른쪽 흰색
  // -> 왼쪽 보정

  else if (
    F_Left == BLACK &&
    F_Right == WHITE
  ) {

    forwardCorrectLeft();

    return true;
  }


  // 왼쪽 흰색 / 오른쪽 검정
  // -> 오른쪽 보정

  else if (
    F_Left == WHITE &&
    F_Right == BLACK
  ) {

    forwardCorrectRight();

    return true;
  }


  // 양쪽 흰색 -> 정지

  else {

    stopMotor();

    return false;
  }
}


// ======================================================
// 후진 라인트레이싱
// ======================================================

bool lineBackward() {

  int B_Left =
    digitalRead(BL_L);

  int B_Right =
    digitalRead(BL_R);


  if (
    B_Left == BLACK &&
    B_Right == BLACK
  ) {

    backwardMotor();

    return true;
  }


  else if (
    B_Left == BLACK &&
    B_Right == WHITE
  ) {

    backwardCorrectLeft();

    return true;
  }


  else if (
    B_Left == WHITE &&
    B_Right == BLACK
  ) {

    backwardCorrectRight();

    return true;
  }


  else {

    stopMotor();

    return false;
  }
}


// ======================================================
// 센서 디버깅
// ======================================================

void debugSensors() {

  if (!SENSOR_DEBUG) {

    return;
  }


  if (
    millis() - sensorDebugTimer >= 300
  ) {

    sensorDebugTimer = millis();


    Serial.print("[SENSOR] FL_L=");
    Serial.print(digitalRead(FL_L));

    Serial.print(" FL_R=");
    Serial.print(digitalRead(FL_R));


    Serial.print(" | BL_L=");
    Serial.print(digitalRead(BL_L));

    Serial.print(" BL_R=");
    Serial.print(digitalRead(BL_R));


    Serial.print(" | L=");
    Serial.print(getLeftSpeed());

    Serial.print(" R=");
    Serial.println(getRightSpeed());
  }
}


// ======================================================
// START
// ======================================================

void beginMission() {

  stopMotor();

  servoDetach();

  motionTicks = 0;

  state = FORWARD_RUN;


  Serial.println(
    "[UNO] FORWARD START"
  );
}


// ======================================================
// RETURN
// ======================================================

void beginReturn() {

  stopMotor();

  servoDetach();

  motionTicks = 0;

  state = RETURN_RUN;


  Serial.println(
    "[UNO] RETURN START"
  );
}


// ======================================================
// BOX 시작
// ======================================================

void beginBox() {

  stopMotor();

  servoPos = INIT_POS;

  servoAttach();

  myservo.write(
    servoPos
  );

  servoTimer =
    millis();

  state =
    BOX_OPENING;


  Serial.println(
    "[UNO] BOX OPEN START"
  );
}


// ======================================================
// AGV RESET
// ======================================================

void resetAgv() {

  stopMotor();

  servoDetach();

  motionTicks = 0;

  state = IDLE;


  Serial.println(
    "[UNO] AGV RESET"
  );
}


// ======================================================
// ESP 명령 처리
// ======================================================

void processCommand(String command) {

  command.trim();


  // ====================================================
  // 빈 문자열 무시
  // ====================================================

  if (
    command.length() == 0
  ) {

    return;
  }


  // ====================================================
  // ESP Debug 메시지
  //
  // 실제 제어 명령으로 실행하지 않는다.
  //
  // ESP:
  // DBG:WIFI_CONNECTED
  // DBG:CONTROL_READY
  // DBG:HEARTBEAT
  // ====================================================

  if (
    command.startsWith("DBG:")
  ) {

    Serial.println(command);

    return;
  }


  // ====================================================
  // 여기부터 실제 명령
  // ====================================================

  Serial.print(
    "[ESP CMD] "
  );

  Serial.println(
    command
  );


  // ====================================================
  // 비상 정지 / 해제
  // ====================================================

  if (command == "EMERGENCY_STOP") {

    stopMotor();
    servoDetach();
    motionTicks = 0;
    emergencyStopLatched = true;
    state = EMERGENCY_STOPPED;

    Serial.println("[UNO] EMERGENCY STOP LATCHED");
    return;
  }

  if (command == "RELEASE_EMERGENCY_STOP") {

    stopMotor();
    servoDetach();
    motionTicks = 0;
    emergencyStopLatched = false;
    state = IDLE;

    Serial.println("[UNO] EMERGENCY STOP RELEASED");
    return;
  }

  // 비상 정지가 걸린 동안에는 해제 명령 이외의 모든 동작을 막는다.
  if (emergencyStopLatched) {
    Serial.println("[UNO] COMMAND IGNORED: EMERGENCY STOP LATCHED");
    return;
  }


  // ====================================================
  // START
  // ====================================================

  if (
    command == "START" ||
    command == "FORWARD"
  ) {

    beginMission();

    Serial.println(
      "[UNO] AGV START"
    );

    return;
  }


  // ====================================================
  // STOP
  // ====================================================

  if (
    command == "STOP"
  ) {

    stopMotor();

    servoDetach();

    motionTicks = 0;

    state = STOPPED;


    Serial.println(
      "[UNO] AGV STOP"
    );

    return;
  }


  // ====================================================
  // RETURN
  // ====================================================

  if (
    command == "RETURN" ||
    command == "RETURN_HOME" ||
    command == "REVERSE"
  ) {

    beginReturn();

    Serial.println(
      "[UNO] AGV RETURN"
    );

    return;
  }


  // ====================================================
  // BOX
  // ====================================================

  if (
    command == "BOX" ||
    command == "BOX_ACTION"
  ) {

    beginBox();

    Serial.println(
      "[UNO] AGV BOX"
    );

    return;
  }


  // ====================================================
  // 속도
  //
  // S:25
  // S:50
  // S:80
  // ====================================================

  if (
    command.startsWith("S:")
  ) {

    int value =
      command.substring(2).toInt();

    setMotorSpeedFromLevel(
      value
    );

    return;
  }


  // ====================================================
  // RESET
  // FastAPI RESET 대응
  // ====================================================

  if (
    command == "RESET"
  ) {

    resetAgv();

    return;
  }


  // ====================================================
  // 알 수 없는 명령
  // ====================================================

  Serial.print(
    "[UNO] UNKNOWN COMMAND: "
  );

  Serial.println(
    command
  );
}


// ======================================================
// ESP 데이터 확인
//
// readStringUntil() 대신 문자 단위로 받아서
// loop가 장시간 멈추지 않도록 처리
// ======================================================

void checkEsp() {

  while (
    espSerial.available() > 0
  ) {

    char c =
      espSerial.read();


    // --------------------------------------------------
    // 줄 종료
    // --------------------------------------------------

    if (
      c == '\n'
    ) {

      espBuffer.trim();


      if (
        espBuffer.length() > 0
      ) {

        processCommand(
          espBuffer
        );
      }


      espBuffer = "";
    }


    // --------------------------------------------------
    // CR 무시
    // --------------------------------------------------

    else if (
      c == '\r'
    ) {

      // ignore
    }


    // --------------------------------------------------
    // 데이터 누적
    // --------------------------------------------------

    else {

      // 비정상적으로 긴 데이터 방지
      if (
        espBuffer.length() < 180
      ) {

        espBuffer += c;
      }

      else {

        Serial.println(
          "[UNO] ESP BUFFER OVERFLOW"
        );

        espBuffer = "";
      }
    }
  }
}


// ======================================================
// BOX 동작
// ======================================================

void updateServoBox() {

  unsigned long now =
    millis();


  // ====================================================
  // OPEN
  // ====================================================

  if (
    state == BOX_OPENING
  ) {

    if (
      now - servoTimer >= 20
    ) {

      servoTimer =
        now;


      if (
        servoPos < OPEN_POS
      ) {

        servoPos++;

        myservo.write(
          servoPos
        );
      }

      else {

        Serial.println(
          "[UNO] BOX OPEN COMPLETE"
        );

        // Keep the PWM signal active while the box is open.  Detaching here
        // releases holding torque, so a loaded or spring-biased box can fall
        // back before the close phase begins.

        stateTimer =
          now;

        state =
          BOX_WAIT;
      }
    }
  }


  // ====================================================
  // WAIT
  // ====================================================

  else if (
    state == BOX_WAIT
  ) {

    if (
      now - stateTimer >= 1000
    ) {

      servoAttach();

      servoTimer =
        now;

      state =
        BOX_CLOSING;


      Serial.println(
        "[UNO] BOX CLOSE START"
      );
    }
  }


  // ====================================================
  // CLOSE
  // ====================================================

  else if (
    state == BOX_CLOSING
  ) {

    if (
      now - servoTimer >= 20
    ) {

      servoTimer =
        now;


      if (
        servoPos > INIT_POS
      ) {

        servoPos--;

        myservo.write(
          servoPos
        );
      }

      else {

        Serial.println(
          "[UNO] BOX CLOSE COMPLETE"
        );


        servoDetach();

        motionTicks = 0;

        state =
          RETURN_RUN;


        Serial.println(
          "[UNO] AUTO RETURN START"
        );
      }
    }
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
  // ESP
  // ====================================================

  espSerial.begin(9600);


  // ====================================================
  // 센서
  // ====================================================

  pinMode(
    FL_R,
    INPUT
  );

  pinMode(
    FL_L,
    INPUT
  );

  pinMode(
    BL_R,
    INPUT
  );

  pinMode(
    BL_L,
    INPUT
  );


  // ====================================================
  // 모터
  // ====================================================

  pinMode(
    A1A,
    OUTPUT
  );

  pinMode(
    A1B,
    OUTPUT
  );

  pinMode(
    B1A,
    OUTPUT
  );

  pinMode(
    B1B,
    OUTPUT
  );


  stopMotor();


  // ====================================================
  // 서보 초기화
  // ====================================================

  servoAttach();

  myservo.write(
    INIT_POS
  );

  delay(500);

  servoDetach();


  // ====================================================
  // 기본 속도
  // ====================================================

  setMotorSpeedFromLevel(
    25
  );


  // ====================================================
  // 시작 메시지
  // ====================================================

  Serial.println();

  Serial.println(
    "================================"
  );

  Serial.println(
    "AGV UNO READY"
  );

  Serial.println(
    "================================"
  );


  Serial.println(
    "Waiting for ESP8266..."
  );


  Serial.println();

  Serial.print(
    "LEFT SPEED = "
  );

  Serial.println(
    getLeftSpeed()
  );


  Serial.print(
    "RIGHT SPEED = "
  );

  Serial.println(
    getRightSpeed()
  );


  Serial.println();
}


// ======================================================
// LOOP
// ======================================================

void loop() {

  // ====================================================
  // ESP 명령 / 로그 수신
  //
  // 가능한 자주 호출해야 함
  // ====================================================

  checkEsp();


  // ====================================================
  // 센서 Debug
  // ====================================================

  debugSensors();


  // ====================================================
  // 상태 Machine
  // ====================================================

  switch (
    state
  ) {


    // ==================================================
    // 전진
    // ==================================================

    case FORWARD_RUN:
    {

      bool moving =
        lineForward();


      if (
        moving
      ) {

        motionTicks++;
      }


      if (
        motionTicks >=
        FORWARD_TICKS
      ) {

        stopMotor();

        Serial.println(
          "[UNO] FORWARD COMPLETE"
        );


        beginBox();
      }


      delay(15);

      break;
    }


    // ==================================================
    // BOX
    // ==================================================

    case BOX_OPENING:

    case BOX_WAIT:

    case BOX_CLOSING:

      updateServoBox();

      break;


    // ==================================================
    // 복귀
    // ==================================================

    case RETURN_RUN:
    {

      bool moving =
        lineBackward();


      if (
        moving
      ) {

        motionTicks++;
      }


      if (
        motionTicks >=
        RETURN_TICKS
      ) {

        stopMotor();

        motionTicks = 0;

        state = IDLE;


        Serial.println(
          "[UNO] RETURN COMPLETE"
        );


        Serial.println(
          "[UNO] AGV CYCLE COMPLETE"
        );
      }


      delay(15);

      break;
    }


    // ==================================================
    // 대기 / 정지
    // ==================================================

    case IDLE:

    case STOPPED:

    default:

      stopMotor();

      delay(5);

      break;
  }
}
