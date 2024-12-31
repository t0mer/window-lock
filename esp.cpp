#include <WiFi.h>
#include <PubSubClient.h>

// WiFi and MQTT configuration
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "YOUR_MQTT_BROKER_IP";

// Client-specific ID
const char* client_id = "window_1";

WiFiClient espClient;
PubSubClient client(espClient);

// GPIO Pins
const int magnetSensorPin = 2;
const int relayPin = 4;

void setup() {
  pinMode(magnetSensorPin, INPUT);
  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, HIGH); // Ensure relay is off initially

  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void setup_wifi() {
  delay(10);
  Serial.println("Connecting to Wi-Fi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("Wi-Fi connected");
}

void callback(char* topic, byte* payload, unsigned int length) {
  char message[length + 1];
  memcpy(message, payload, length);
  message[length] = '\0';

  DynamicJsonDocument doc(256);
  deserializeJson(doc, message);

  const char* command = doc["command"];
  const char* target_client_id = doc["client_id"];

  if (target_client_id && strcmp(target_client_id, client_id) != 0) {
    return; // Ignore commands not targeted to this client
  }

  if (strcmp(command, "get_status") == 0) {
    int windowState = digitalRead(magnetSensorPin);
    const char* state = (windowState == HIGH) ? "closed" : "open";
    String response = String("{\"client_id\":\"") + client_id + "\",\"message\":\"Window is " + state + "\"}";
    client.publish("window/response", response.c_str());
  }

  if (strcmp(command, "lock_window") == 0) {
    int windowState = digitalRead(magnetSensorPin);
    if (windowState == HIGH) { // Only lock if window is closed
      digitalWrite(relayPin, LOW); // Activate lock
      delay(1000);
      digitalWrite(relayPin, HIGH); // Deactivate lock
      String response = String("{\"client_id\":\"") + client_id + "\",\"message\":\"Window locked\"}";
      client.publish("window/response", response.c_str());
    } else {
      String response = String("{\"client_id\":\"") + client_id + "\",\"message\":\"Window is open, cannot lock\"}";
      client.publish("window/response", response.c_str());
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect(client_id)) {
      client.subscribe("window/command");
    } else {
      delay(5000);
    }
  }
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
}
