import os
import time
import joblib
import pandas as pd
import requests
from django.core.management.base import BaseCommand

API_LATEST = "http://localhost:8080/api/latest-sensor/"
API_PREV = "http://localhost:8080/api/prev-sensor/"

class Command(BaseCommand):
    help = 'Run ML-based emergency detection using sensor data from API.'

    def sanitize(self, value, min_val=0, max_val=10000):
        try:
            val = float(value)
            if min_val <= val <= max_val:
                return val
        except:
            pass
        return 0.0

    def determine_risk_level(self, prediction, proba, latest):
        motion = any(latest.get("motion", []))
        door = any(latest.get("cmk", []))
        button = latest.get("button")

        if button:
            return "🔥 HIGH - PANIC BUTTON PRESSED"

        if prediction == 1 and proba > 0.8 and (motion or door):
            return "🔥 HIGH - Confirmed by context sensors"

        if prediction == 1 and proba > 0.6:
            return "🚨 MEDIUM - ML triggered without confirmation"

        if (
            latest.get("temperature", 0) > 45 or
            latest.get("gas", 0) > 900
        ):
            return "⚠️ LOW - Slightly elevated sensor values"

        return "✅ NORMAL - All conditions stable"

    def rate_of_change_check(self, latest, prev):
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
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                self.stderr.write(f"Failed to fetch from {url}: {response.status_code}")
        except Exception as e:
            self.stderr.write(f"Error connecting to {url}: {e}")
        return None

    def handle(self, *args, **options):
        print("🤖 Starting ML emergency detection loop (via API)...\n")

        try:
            model = joblib.load("ml_emergency_model_data.pkl")
        except FileNotFoundError:
            self.stderr.write("⚠️ Model not found. Run training script first.")
            self.stderr.write(str(os.listdir()))
            return

        while True:
            latest = self.fetch_data(API_LATEST)
            if not latest:
                print("No latest sensor data available.")
                time.sleep(5)
                continue

            prev = self.fetch_data(API_PREV)
            if not self.rate_of_change_check(latest, prev):
                print("❌ Skipping analysis due to suspected noise.")
                time.sleep(5)
                continue

            print(f"\n📅 Timestamp: {latest.get('timestamp')}")
            print(f"🏠 Device ID: {latest.get('device_id')} ({latest.get('controller')})")
            print(f"🌡️ Temp: {latest.get('temperature')} °C")
            print(f"💧 Humidity: {latest.get('humidity')} %")
            print(f"🔥 Gas: {latest.get('gas')}")
            print(f"🔴 Button: {latest.get('button')}")

            input_data = pd.DataFrame([{
                "temperature": self.sanitize(latest.get("temperature"), 0, 100),
                "humidity": self.sanitize(latest.get("humidity"), 0, 100),
                "gas": self.sanitize(latest.get("gas"), 0, 5000),
                "button": 1 if latest.get("button") else 0,
            }])

            prediction = model.predict(input_data)[0]
            proba = model.predict_proba(input_data)[0][1]

            if prediction == 1:
                print(f"\n🚨 EMERGENCY DETECTED (ML Prediction: {proba:.2%})")
            else:
                print(f"\n✅ Normal (ML Prediction: {proba:.2%})")

            risk_level = self.determine_risk_level(prediction, proba, latest)
            print(f"\n🧩 RISK LEVEL: {risk_level}")

            time.sleep(5)
