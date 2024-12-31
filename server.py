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
