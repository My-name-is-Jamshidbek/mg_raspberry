import json
import time
import requests

from django.core.management.base import BaseCommand, CommandError
import paho.mqtt.client as mqtt

# MQTT connection settings
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "room102/data"
MQTT_USER = ""    # Update if needed
MQTT_PASS = ""    # Update if needed

# Django API endpoint to save sensor data
API_URL = "http://localhost:80/api/save-sensor-data/"  # Adjust for production

class Command(BaseCommand):
    help = 'Subscribe to MQTT and send data to Django API'

    def handle(self, *args, **options):
        self.stdout.write("🚀 Starting MQTT subscriber...")

        client = mqtt.Client()

        if MQTT_USER or MQTT_PASS:
            client.username_pw_set(MQTT_USER, MQTT_PASS)

        client.on_connect = self.on_connect
        client.on_message = self.on_message

        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        except Exception as e:
            raise CommandError(f"Unable to connect to MQTT broker: {e}")

        client.loop_start()
        self.stdout.write("✅ MQTT connected. Listening for messages... (Press Ctrl+C to exit)")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write("🛑 Stopping MQTT subscriber...")
            client.loop_stop()
            client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.stdout.write("✅ Connected to MQTT broker.")
            client.subscribe(MQTT_TOPIC)
            self.stdout.write(f"📡 Subscribed to topic: {MQTT_TOPIC}")
        else:
            self.stdout.write(f"❌ MQTT connection failed. Return code: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            message = msg.payload.decode()
            self.stdout.write(f"📥 MQTT message received: {message}")
            data = json.loads(message)
            print(data)
            response = requests.post(API_URL, json=data)
            if response.status_code == 201:
                self.stdout.write("✅ Sensor data saved via API.")
            else:
                self.stdout.write(f"❌ API Error: {response.status_code} - {response.text}")
        except Exception as e:
            self.stdout.write(f"❌ Failed to process MQTT message: {e}")
