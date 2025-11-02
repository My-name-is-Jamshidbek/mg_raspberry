import json
import random
import threading
import time
from datetime import datetime
import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# MQTT Configuration
MQTT_BROKER = "10.212.157.202"
MQTT_PORT = 1883
MQTT_USER = ""
MQTT_PASS = ""
MQTT_TOPIC = "room102/data"
DEVICE_ID = "1"
CONTROLLER = "NodeMCU"

# Sensor Data Ranges
TEMP_MIN = 15.0
TEMP_MAX = 30.0
HUMIDITY_MIN = 30.0
HUMIDITY_MAX = 80.0
GAS_PPM_MIN = 200.0
GAS_PPM_MAX = 1500.0


class MQTTSimulator:
    """Simulate Arduino sensor data and publish to MQTT"""
    
    def __init__(self, broker=MQTT_BROKER, port=MQTT_PORT, 
                 user=MQTT_USER, password=MQTT_PASS, topic=MQTT_TOPIC):
        self.broker = broker
        self.port = port
        self.user = user
        self.password = password
        self.topic = topic
        self.client = mqtt.Client()
        self.is_running = False
        self.thread = None
        
        # Set up callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        
    def on_connect(self, client, userdata, flags, rc):
        """Called when the client connects to the broker"""
        if rc == 0:
            logger.info(f"MQTT connected to {self.broker}:{self.port}")
        else:
            logger.error(f"MQTT connection failed with rc={rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Called when the client disconnects from the broker"""
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT (rc={rc})")
    
    def on_publish(self, client, userdata, mid):
        """Called when a message is published"""
        logger.debug(f"Message published with mid={mid}")
    
    def generate_sensor_data(self):
        """Generate realistic fake sensor data"""
        # Add slight variations to make data more realistic
        temperature = round(random.uniform(TEMP_MIN, TEMP_MAX), 2)
        humidity = round(random.uniform(HUMIDITY_MIN, HUMIDITY_MAX), 2)
        ppm = round(random.uniform(GAS_PPM_MIN, GAS_PPM_MAX), 2)
        
        # Digital sensors (simulating PIR motion sensors, door contact switches, button)
        cmk1 = random.choice([True, False])  # Contact switch 1
        cmk2 = random.choice([True, False])  # Contact switch 2
        pir1 = random.choice([True, False])  # Motion sensor 1
        pir2 = random.choice([True, False])  # Motion sensor 2
        button = random.choice([True, False])  # Button state
        
        return {
            "device_id": DEVICE_ID,
            "controller": CONTROLLER,
            "temperature": temperature,
            "humidity": humidity,
            "cmk": [cmk1, cmk2],
            "motion": [pir1, pir2],
            "button": button,
            "gas": ppm,
            "timestamp": datetime.now().isoformat()
        }
    
    def publish_data(self):
        """Continuously publish sensor data to MQTT"""
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            
            while self.is_running:
                try:
                    sensor_data = self.generate_sensor_data()
                    payload = json.dumps(sensor_data)
                    
                    result = self.client.publish(self.topic, payload)
                    
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        logger.info(f"Published: {payload}")
                    else:
                        logger.error(f"Failed to publish: {result.rc}")
                    
                    time.sleep(1)  # Send data every second
                    
                except Exception as e:
                    logger.error(f"Error in publish loop: {str(e)}")
                    time.sleep(1)
        
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
        
        finally:
            self.client.loop_stop()
            self.client.disconnect()
    
    def start(self):
        """Start the simulator in a background thread"""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self.publish_data, daemon=True)
            self.thread.start()
            logger.info("MQTT Simulator started")
    
    def stop(self):
        """Stop the simulator"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("MQTT Simulator stopped")


# Django Management Command
class Command(BaseCommand):
    """Django management command to run MQTT simulator"""
    help = "Run MQTT simulator to send fake sensor data"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--broker',
            type=str,
            default=MQTT_BROKER,
            help='MQTT broker address'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=MQTT_PORT,
            help='MQTT broker port'
        )
        parser.add_argument(
            '--topic',
            type=str,
            default=MQTT_TOPIC,
            help='MQTT topic to publish to'
        )
        parser.add_argument(
            '--duration',
            type=int,
            default=None,
            help='Duration in seconds (None for infinite)'
        )
    
    def handle(self, *args, **options):
        broker = options['broker']
        port = options['port']
        topic = options['topic']
        duration = options['duration']
        
        simulator = MQTTSimulator(broker=broker, port=port, topic=topic)
        simulator.start()
        
        try:
            if duration:
                self.stdout.write(
                    self.style.SUCCESS(f"Running simulator for {duration} seconds...")
                )
                time.sleep(duration)
            else:
                self.stdout.write(
                    self.style.SUCCESS("Simulator running (Ctrl+C to stop)...")
                )
                while True:
                    time.sleep(1)
        
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nShutting down..."))
        
        finally:
            simulator.stop()
            self.stdout.write(self.style.SUCCESS("Simulator stopped"))