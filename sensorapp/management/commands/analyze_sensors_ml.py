import os
import time
import joblib
import pandas as pd
from django.core.management.base import BaseCommand
from sensorapp.models import SensorData

class Command(BaseCommand):
    help = 'Run ML-based emergency detection with risk levels and noise protection.'

    def sanitize(self, value, min_val=0, max_val=10000):
        try:
            val = float(value)
            if min_val <= val <= max_val:
                return val
        except:
            pass
        return 0.0

    def determine_risk_level(self, prediction, proba, latest):
        motion = any(latest.motion) if latest.motion else False
        door = any(latest.cmk) if latest.cmk else False
        button = latest.button

        if button:
            return "🔥 HIGH - PANIC BUTTON PRESSED"

        if prediction == 1 and proba > 0.8 and (motion or door):
            return "🔥 HIGH - Confirmed by context sensors"

        if prediction == 1 and proba > 0.6:
            return "🚨 MEDIUM - ML triggered without confirmation"

        if (
            (latest.temperature and latest.temperature > 45) or
            (latest.gas and latest.gas > 900)
        ):
            return "⚠️ LOW - Slightly elevated sensor values"

        return "✅ NORMAL - All conditions stable"

    def rate_of_change_check(self, latest, prev):
        if not prev:
            return True

        temp_delta = abs((latest.temperature or 0) - (prev.temperature or 0))
        gas_delta = abs((latest.gas or 0) - (prev.gas or 0))

        if temp_delta > 20:
            self.stdout.write(f"⚠️  Large temperature change detected: {temp_delta} °C")
            return False

        if gas_delta > 500:
            self.stdout.write(f"⚠️  Large gas change detected: {gas_delta}")
            return False

        return True

    def handle(self, *args, **options):
        print("🤖 Starting ML emergency detection loop...\n")

        try:
            model = joblib.load("ml_emergency_model_data.pkl")
        except FileNotFoundError:
            self.stderr.write("⚠️ Model not found. Run training script first.")
            self.stderr.write(str(os.listdir()))
            return

        while True:
            latest = SensorData.objects.order_by('-timestamp').first()
            if not latest:
                print("No sensor data available.")
                time.sleep(5)
                continue

            prev = SensorData.objects.exclude(id=latest.id).order_by('-timestamp').first()
            if not self.rate_of_change_check(latest, prev):
                print("❌ Skipping analysis due to suspected noise.")
                time.sleep(5)
                continue

            print(f"\n📅 Timestamp: {latest.timestamp}")
            print(f"🏠 Device ID: {latest.device_id} ({latest.controller})")
            print(f"🌡️ Temp: {latest.temperature} °C")
            print(f"💧 Humidity: {latest.humidity} %")
            print(f"🔥 Gas: {latest.gas}")
            print(f"🔴 Button: {latest.button}")

            input_data = pd.DataFrame([{
                "temperature": self.sanitize(latest.temperature, 0, 100),
                "humidity": self.sanitize(latest.humidity, 0, 100),
                "gas": self.sanitize(latest.gas, 0, 5000),
                "button": 1 if latest.button else 0,
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
