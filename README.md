1. Updated Requirements for Server
Unique Client Identification:

Messages include a client_id for targeted communication.
The server can send commands to all clients or a specific one.
Device Network Monitoring:

Use fping to check the availability of devices (e.g., phones).
If no devices respond, notify via Telegram.


Server Implementation
a. Install Additional Dependencies
Install fping, mosquitto mqtt broker:
```bash
sudo apt install fping mosquitto mosquitto-clients python3-pip -y
```

Install Python and Dependencies
```bash
pip3 install python-telegram-bot paho-mqtt
```


## Server Implementation
```python
import os
import time
import json
import paho.mqtt.client as mqtt
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# MQTT configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC_COMMAND = "window/command"
TOPIC_RESPONSE = "window/response"

# Telegram bot token
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ALERT_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# Network devices to monitor (replace with IPs of phones/devices)
MONITORED_DEVICES = ["192.168.1.10", "192.168.1.11"]

# MQTT client
mqtt_client = mqtt.Client()

def on_mqtt_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with code {rc}")
    client.subscribe(TOPIC_RESPONSE)

def on_mqtt_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    client_id = payload.get("client_id", "Unknown")
    message = payload.get("message", "")
    updater.bot.send_message(chat_id=ALERT_CHAT_ID, text=f"[{client_id}] {message}")

mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message

mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
mqtt_client.loop_start()

# Command to check window status
def check_status(update: Update, context: CallbackContext):
    if len(context.args) > 0:
        client_id = context.args[0]
        mqtt_client.publish(TOPIC_COMMAND, json.dumps({"client_id": client_id, "command": "get_status"}))
        update.message.reply_text(f"Requested status from client {client_id}")
    else:
        mqtt_client.publish(TOPIC_COMMAND, json.dumps({"command": "get_status"}))
        update.message.reply_text("Requested status from all clients")

# Command to lock windows
def lock_window(update: Update, context: CallbackContext):
    if len(context.args) > 0:
        client_id = context.args[0]
        mqtt_client.publish(TOPIC_COMMAND, json.dumps({"client_id": client_id, "command": "lock_window"}))
        update.message.reply_text(f"Sent lock command to client {client_id}")
    else:
        mqtt_client.publish(TOPIC_COMMAND, json.dumps({"command": "lock_window"}))
        update.message.reply_text("Sent lock command to all clients")

# Monitor network devices
def monitor_devices():
    while True:
        unreachable_count = 0
        for device in MONITORED_DEVICES:
            response = os.system(f"fping -c1 -t300 {device} >/dev/null 2>&1")
            if response != 0:
                unreachable_count += 1

        if unreachable_count == len(MONITORED_DEVICES):
            updater.bot.send_message(chat_id=ALERT_CHAT_ID, text="No monitored devices are responding!")

        time.sleep(60)

# Start Telegram bot
updater = Updater(TELEGRAM_BOT_TOKEN)
dispatcher = updater.dispatcher

dispatcher.add_handler(CommandHandler("check_status", check_status))
dispatcher.add_handler(CommandHandler("lock_window", lock_window))

# Run network monitor in a separate thread
import threading
threading.Thread(target=monitor_devices, daemon=True).start()

updater.start_polling()
updater.idle()
```


## Client (ESP32/ESP8266) Implementation
```cpp
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
```


## Features Overview
### Server:

* Publishes commands to all clients or specific clients.
* Monitors network devices and sends Telegram notifications if none respond.
* Provides Telegram commands for status checks and locking.

## Client:

* Responds to MQTT commands for checking status or locking windows.
* Ensures actions are taken only when conditions are met (e.g., window closed before locking).
* This structure ensures robust and scalable handling of multiple clients and network monitoring.
