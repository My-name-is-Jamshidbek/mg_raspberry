import json
import time

from django.core.management.base import BaseCommand, CommandError
from sensorapp.models import SensorData

import paho.mqtt.client as mqtt

# MQTT connection settings
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "room102/data"
MQTT_USER = ""    # Update if needed
MQTT_PASS = ""    # Update if needed

class Command(BaseCommand):
    help = 'Subscribe to MQTT topic and record sensor data with timestamp'

    def handle(self, *args, **options):
        self.stdout.write("Starting MQTT subscriber...")

        # Create MQTT client instance
        client = mqtt.Client()
        if MQTT_USER or MQTT_PASS:
            client.username_pw_set(MQTT_USER, MQTT_PASS)

        # Define on_connect and on_message callbacks
        client.on_connect = self.on_connect
        client.on_message = self.on_message

        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        except Exception as e:
            raise CommandError(f"Unable to connect to MQTT broker: {e}")

        client.loop_start()
        self.stdout.write("MQTT subscriber started. Press Ctrl+C to exit.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write("Exiting MQTT subscriber...")
            client.loop_stop()
            client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.stdout.write("Connected to MQTT broker successfully.")
            client.subscribe(MQTT_TOPIC)
            self.stdout.write(f"Subscribed to topic: {MQTT_TOPIC}")
        else:
            self.stdout.write(f"Failed to connect, return code {rc}")

    def on_message(self, client, userdata, msg):
        message = msg.payload.decode()
        self.stdout.write(f"Received message on {msg.topic}: {message}")
        try:
            data = json.loads(message)
        except Exception as e:
            self.stdout.write(f"Error decoding JSON: {e}")
            return

        # Create and save a SensorData instance from the incoming data.
        sensor_record = SensorData(
            device_id   = data.get("device_id", ""),
            controller  = data.get("controller", ""),
            temperature = data.get("temperature", None),
            humidity    = data.get("humidity", None),
            cmk         = data.get("cmk", []),
            motion      = data.get("motion", []),
            button      = data.get("button", False),
            gas         = data.get("gas", None)
        )
        try:
            sensor_record.save()
            self.stdout.write("Sensor data saved to database.")
        except Exception as e:
            self.stdout.write(f"Error saving sensor data: {e}")
