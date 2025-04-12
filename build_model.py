import pandas as pd
import joblib
import random
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Step 1: Generate synthetic data
def generate_fake_data(n=5000):
    data = []
    for _ in range(n):
        temp = round(random.uniform(15, 90), 1)
        humidity = round(random.uniform(20, 80), 1)
        gas = round(random.uniform(100, 3000), 1)
        button = random.choice([0, 0, 0, 1])  # rare panic press

        # Fire condition
        fire = temp > 40 and gas > 100
        motion = random.choice([[], [True, False], [False, False]])
        cmk = random.choice([[], [True, False], [False, True]])

        label = int(fire or button or (True in motion))

        data.append({
            "temperature": temp,
            "humidity": humidity,
            "gas": gas,
            "button": button,
            "motion": motion,
            "cmk": cmk,
            "label": label
        })
    return pd.DataFrame(data)

df = generate_fake_data(100000)
print(f"🧪 Generated {len(df)} fake sensor records.")

# Step 2: Prepare training data
X = df[["temperature", "humidity", "gas", "button"]]
y = df["label"]

# Step 3: Train model
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Step 4: Evaluate
y_pred = model.predict(X_test)
print("\n📊 Classification Report:")
print(classification_report(y_test, y_pred))


# Step 5: Save model
joblib.dump(model, "ml_emergency_model_data.pkl")
print("✅ Model saved as ml_emergency_model_data.pkl")
