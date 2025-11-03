import os
import time
import joblib
import pandas as pd
import requests
from django.core.management.base import BaseCommand
from datetime import datetime

API_LATEST = "http://localhost:80/api/latest-sensor/"
API_PREV = "http://localhost:80/api/prev-sensor/"
API_SENSOR_DATA = "http://mg.thejoma.uz/api/home-devices/sensor-data"

# Default configuration
HOME_ID = os.getenv("HOME_ID", 1)
DEVICE_ID = os.getenv("DEVICE_ID", 1)
NORMAL_INTERVAL = 10  # Send every 10 seconds
RISK_INTERVAL = 1    # Send every 1 second if risk detected

class Command(BaseCommand):
    help = 'Run ML-based emergency detection and send sensor data to server.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_send_time = 0
        self.current_risk_level = "NORMAL"

    def sanitize(self, value, min_val=0, max_val=10000):
        try:
            val = float(value)
            if min_val <= val <= max_val:
                return val
        except:
            pass
        return 0.0

    def determine_risk_level(self, prediction, proba, latest):
        """Determine risk level and return status"""
        motion = any(latest.get("motion", []))
        door = any(latest.get("cmk", []))
        button = latest.get("button")

        if button:
            return "HIGH", "PANIC BUTTON PRESSED"

        if prediction == 1 and proba > 0.8 and (motion or door):
            return "HIGH", "Confirmed by context sensors"

        if prediction == 1 and proba > 0.6:
            return "MEDIUM", "ML triggered without confirmation"

        if (
            latest.get("temperature", 0) > 45 or
            latest.get("gas", 0) > 900
        ):
            return "LOW", "Slightly elevated sensor values"

        return "NORMAL", "All conditions stable"

    def rate_of_change_check(self, latest, prev):
        """Check for anomalous rate of change in sensor values"""
        if not prev:
            return True

        temp_delta = abs((latest.get("temperature") or 0) - (prev.get("temperature") or 0))
        gas_delta = abs((latest.get("gas") or 0) - (prev.get("gas") or 0))

        if temp_delta > 20:
            self.stdout.write(f"⚠️  Large temperature change detected: {temp_delta} °C")
            return False

        if gas_delta > 500:
            self.stdout.write(f"⚠️  Large gas change detected: {gas_delta}")
            return False

        return True

    def fetch_data(self, url):
        """Fetch data from API endpoint"""
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                self.stderr.write(f"Failed to fetch from {url}: {response.status_code}")
        except Exception as e:
            self.stderr.write(f"Error connecting to {url}: {e}")
        return None

    def send_sensor_data(self, latest, risk_level, risk_status):
        """Send sensor data to server API"""
        try:
            # Extract motion and door/cmk data
            motion_status = any(latest.get("motion", []))
            door_status = any(latest.get("cmk", []))
            
            payload = {
                "home_id": int(HOME_ID),
                "device_id": int(DEVICE_ID),
                "sensors": {
                    "1": self.sanitize(latest.get("temperature"), 0, 100),
                    "2": self.sanitize(latest.get("humidity"), 0, 100),
                    "3": self.sanitize(latest.get("gas"), 0, 5000),
                    "4": 1 if motion_status else 0,                    # motion
                    "5": 1 if door_status else 0,                      # door/cmk
                    "6": 1 if latest.get("button") else 0,             # button
                },
                "home": {
                    "status": risk_level.lower()
                }
            }

            response = requests.post(
                API_SENSOR_DATA,
                json=payload,
                timeout=5
            )

            if response.status_code in [200, 201]:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Sent 6 sensors - Risk: {risk_level} ({risk_status})"
                    )
                )
                return True
            else:
                self.stderr.write(
                    f"❌ Failed to send data: {response.status_code}"
                )
                return False

        except Exception as e:
            self.stderr.write(f"Error sending sensor data: {e}")
            return False

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("🤖 Starting ML emergency detection service...\n")
        )

        try:
            model = joblib.load("ml_emergency_model_data.pkl")
        except FileNotFoundError:
            self.stderr.write("⚠️ Model not found. Run training script first.")
            self.stderr.write(str(os.listdir()))
            return

        self.stdout.write(f"Configuration:")
        self.stdout.write(f"  Home ID: {HOME_ID}")
        self.stdout.write(f"  Device ID: {DEVICE_ID}")
        self.stdout.write(f"  Normal send interval: {NORMAL_INTERVAL}s")
        self.stdout.write(f"  Risk send interval: {RISK_INTERVAL}s\n")

        try:
            while True:
                current_time = time.time()

                # Fetch latest sensor data
                latest = self.fetch_data(API_LATEST)
                print(F"Latest data: {latest}")
                if not latest:
                    self.stdout.write("⏳ No latest sensor data available.")
                    time.sleep(NORMAL_INTERVAL)
                    continue

                # Rate of change validation
                prev = self.fetch_data(API_PREV)
                if not self.rate_of_change_check(latest, prev):
                    self.stdout.write("❌ Skipping analysis due to suspected noise.")
                    time.sleep(NORMAL_INTERVAL)
                    continue

                # ML prediction
                input_data = pd.DataFrame([{
                    "temperature": self.sanitize(latest.get("temperature"), 0, 100),
                    "humidity": self.sanitize(latest.get("humidity"), 0, 100),
                    "gas": self.sanitize(latest.get("gas"), 0, 5000),
                    "button": 1 if latest.get("button") else 0,
                }])

                prediction = model.predict(input_data)[0]
                proba_array = model.predict_proba(input_data)[0]
                
                # Handle probability extraction safely
                if len(proba_array) > 1:
                    proba = proba_array[1]  # Probability of positive class
                else:
                    # If only one class probability, use it directly
                    proba = proba_array[0]

                # Determine risk level
                risk_level, risk_status = self.determine_risk_level(prediction, proba, latest)

                # Log analysis results
                self.stdout.write(f"\n📅 {datetime.now().strftime('%H:%M:%S')}")
                self.stdout.write(f"🏠 Device: {latest.get('device_id')} ({latest.get('controller')})")
                self.stdout.write(f"🌡️  Temp: {latest.get('temperature')}°C | 💧 Humidity: {latest.get('humidity')}% | 🔥 Gas: {latest.get('gas')}")

                if prediction == 1:
                    self.stdout.write(
                        self.style.WARNING(f"🚨 EMERGENCY DETECTED (Confidence: {proba:.2%})")
                    )
                else:
                    self.stdout.write(f"✅ Normal (Confidence: {proba:.2%})")

                self.stdout.write(
                    self.style.SUCCESS(f"🧩 Risk Level: {risk_level} - {risk_status}")
                )

                # Determine send interval based on risk level
                send_interval = RISK_INTERVAL if risk_level != "NORMAL" else NORMAL_INTERVAL

                # Send data if interval has passed
                if current_time - self.last_send_time >= send_interval:
                    self.send_sensor_data(latest, risk_level, risk_status)
                    self.last_send_time = current_time

                self.current_risk_level = risk_level

                # Sleep before next analysis
                time.sleep(1)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n⏹️  Service stopped by user."))
