#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include "DHT.h"
#include <MPU6050.h>

const char* ssid = "Max";
const char* password = "pankaj123";
const char* server = "http://healthcare.pythonanywhere.com/api/data/";

#define DHTPIN 4
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

MPU6050 mpu;

#define BUZZER_PIN 27
#define BUTTON_PIN 26

int patient_id = 1;

// MPU6050 communication thresholds in g.
// Calibrate these values for the patient's actual hand/arm movement.
#define GESTURE_X_POS 0.70
#define GESTURE_Y_POS 0.70
#define GESTURE_Z_EMERGENCY 1.30
#define GESTURE_X_NEG -0.70

String pendingRequest = "NONE";
unsigned long emergencyBuzzerUntil = 0;

void beep(int count) {
  for (int i = 0; i < count; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(180);
    digitalWrite(BUZZER_PIN, LOW);
    delay(180);
  }
}

String detectButtonRequest() {
  int presses = 0;
  unsigned long start = millis();

  while (millis() - start < 2000) {
    if (digitalRead(BUTTON_PIN) == LOW) {
      presses++;
      while (digitalRead(BUTTON_PIN) == LOW) delay(20);
      delay(120);
    }
    delay(10);
  }

  if (presses == 1) return "EMERGENCY";
  if (presses == 2) return "WATER";
  if (presses == 3) return "FOOD";
  if (presses == 4) return "MEDICINE";
  return "NONE";
}

void handleRequestBuzzer(String request) {
  if (request == "EMERGENCY") {
    digitalWrite(BUZZER_PIN, HIGH);
    emergencyBuzzerUntil = millis() + 5000;
  } else if (request == "WATER") {
    beep(2);
  } else if (request == "FOOD") {
    beep(3);
  } else if (request == "MEDICINE") {
    beep(4);
  }
}

String detectMovementRequest(float x, float y, float z) {
  if (x > GESTURE_X_POS) return "FOOD";
  if (y > GESTURE_Y_POS) return "WATER";
  if (z > GESTURE_Z_EMERGENCY) return "EMERGENCY";
  if (x < GESTURE_X_NEG) return "SLEEP";
  return "NONE";
}

void setup() {
  Serial.begin(115200);

  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  digitalWrite(BUZZER_PIN, LOW);

  dht.begin();

  Wire.begin(21, 22);
  mpu.initialize();

  if (mpu.testConnection()) {
    Serial.println("MPU6050 Connected");
  } else {
    Serial.println("MPU6050 Error");
  }

  WiFi.begin(ssid, password);
  Serial.print("Connecting WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
}

void loop() {

  // Button communication: count 1-4 presses in a 2-second window.
  // The request is generated only when a press sequence is detected.
  if (digitalRead(BUTTON_PIN) == LOW) {
    pendingRequest = detectButtonRequest();

    if (pendingRequest != "NONE") {
      Serial.println("BUTTON REQUEST: " + pendingRequest);
      handleRequestBuzzer(pendingRequest);
    }
  }

  if (millis() < emergencyBuzzerUntil) {
    digitalWrite(BUZZER_PIN, HIGH);
  } else if (pendingRequest != "EMERGENCY") {
    digitalWrite(BUZZER_PIN, LOW);
  }

  if (WiFi.status() == WL_CONNECTED) {

    float temp = dht.readTemperature();
    float humidity = dht.readHumidity();

    if (isnan(temp) || isnan(humidity)) {
      Serial.println("DHT Error!");
      delay(2000);
      return;
    }

    // Calibration offset for wrist-area prototype.
    // Replace +3.0 after comparison with a reference thermometer.
    temp += 3.0;

    bool highTemp = temp >= 38.0;

    int16_t ax, ay, az;
    mpu.getAcceleration(&ax, &ay, &az);

    float x = ax / 16384.0;
    float y = ay / 16384.0;
    float z = az / 16384.0;

    String movementRequest = detectMovementRequest(x, y, z);

    // Movement emergency also activates the buzzer.
    if (movementRequest == "EMERGENCY") {
      digitalWrite(BUZZER_PIN, HIGH);
    }

    // High temperature activates the buzzer.
    if (highTemp) {
      digitalWrite(BUZZER_PIN, HIGH);
    }

    Serial.println("Temp: " + String(temp, 1) + " °C");
    Serial.println("Humidity: " + String(humidity, 1) + " %");
    Serial.println("X: " + String(x, 3) +
                   " Y: " + String(y, 3) +
                   " Z: " + String(z, 3));
    Serial.println("Movement request: " + movementRequest);

    HTTPClient http;
    http.begin(server);
    http.addHeader("Content-Type", "application/json");

    String json = "{";
    json += "\"patient_id\":" + String(patient_id) + ",";
    json += "\"temperature\":" + String(temp, 2) + ",";
    json += "\"humidity\":" + String(humidity, 2) + ",";
    json += "\"ax\":" + String(x, 3) + ",";
    json += "\"ay\":" + String(y, 3) + ",";
    json += "\"az\":" + String(z, 3) + ",";
    json += "\"movement_request\":\"" + movementRequest + "\",";
    json += "\"patient_request\":\"" + pendingRequest + "\",";
    json += "\"high_temperature\":" + String(highTemp ? "true" : "false") + ",";
    json += "\"emergency\":" + String(
      (pendingRequest == "EMERGENCY" || movementRequest == "EMERGENCY") ? "true" : "false"
    );
    json += "}";

    int response = http.POST(json);

    Serial.println("Response: " + String(response));
    http.end();

    // A button request is an event, so send it once and clear it.
    pendingRequest = "NONE";

    // Don't allow a normal request to leave the buzzer on.
    if (!highTemp && movementRequest != "EMERGENCY" && millis() >= emergencyBuzzerUntil) {
      digitalWrite(BUZZER_PIN, LOW);
    }
  }

  delay(2000);
}
