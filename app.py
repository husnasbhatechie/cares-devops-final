from flask import Flask, render_template, request, redirect, url_for, send_file
import time
import csv
import os

from sklearn.ensemble import IsolationForest
from sklearn.metrics import confusion_matrix, accuracy_score

app = Flask(__name__)

# 🔥 GLOBAL STATE
failure_count = 0
failure_start = None
failure_active = False
total_requests = 0

chaos_mode = None
last_mttr = 0

# 🤖 AI DATA
X_data = []
y_true = []
y_pred = []

model = IsolationForest(contamination=0.2, random_state=42)

# =========================
# 📝 LOGGING
# =========================
def log_data(temp, hum, failure, status, mttr):

    file_exists = os.path.isfile("logs.csv")

    with open("logs.csv", "a", newline="") as file:

        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(["Temp", "Humidity", "Failure", "Status", "MTTR"])

        writer.writerow([temp, hum, failure, status, mttr])

# =========================
# DOWNLOAD LOG
# =========================
@app.route('/download')
def download_logs():
    return send_file("logs.csv", as_attachment=True)

# =========================
# CHAOS
# =========================
@app.route('/inject/<mode>')
def inject(mode):

    global chaos_mode

    chaos_mode = mode

    return redirect(url_for('index'))

# =========================
# MAIN
# =========================
@app.route('/', methods=['GET', 'POST'])
def index():

    global failure_count
    global failure_start
    global failure_active
    global total_requests
    global chaos_mode
    global last_mttr
    global X_data
    global y_true
    global y_pred

    temperature = None
    humidity = None
    failure = ""
    status = ""
    decision = ""
    mttr = 0
    failure_rate = 0
    accuracy = 0
    cm_data = [[0,0],[0,0]]

    if request.method == 'POST':

        total_requests += 1

        temperature = float(request.form.get('temperature') or 25)
        humidity = float(request.form.get('humidity') or 50)

        # 🔥 CHAOS
        if chaos_mode == "sensor":
            temperature = 80

        elif chaos_mode == "network":
            temperature = 0
            humidity = 0

        elif chaos_mode == "drift":
            temperature = 38

        # =========================
        # ✅ RULE BASED FAILURE
        # =========================
        if temperature > 200:

            failure = "Data Corruption"
            status = "RED"
            y_true.append(1)

        elif temperature == 0 and humidity == 0:

            failure = "Network Failure"
            status = "RED"
            y_true.append(1)

        elif temperature > 45 or humidity > 90:

            failure = "Sensor Failure"
            status = "RED"
            y_true.append(1)

        elif temperature > 35:

            failure = "Drift"
            status = "ORANGE"
            y_true.append(0)

        else:

            failure = "No Failure"
            status = "GREEN"
            y_true.append(0)

        # =========================
        # 🤖 AI MODEL
        # =========================
        X_data.append([temperature, humidity])

        if len(X_data) > 10:

            model.fit(X_data)

            pred = model.predict([[temperature, humidity]])[0]

            y_pred.append(1 if pred == -1 else 0)

        else:

            y_pred.append(0)

        # =========================
        # 🔥 FAILURE TIMER
        # =========================
        if status == "RED" and not failure_active:

            failure_active = True
            failure_start = time.time()
            failure_count += 1
            last_mttr = 0

        # =========================
        # 🔧 SELF HEAL
        # =========================
        if chaos_mode == "reset" and failure_active:

            recovery_time = time.time() - failure_start

            if recovery_time < 30:
                last_mttr = recovery_time

            failure_active = False
            failure_start = None
            chaos_mode = None

            temperature = 25
            humidity = 50
            status = "GREEN"
            failure = "Recovered"

            decision = "🔧 Self Healing Completed"

        # =========================
        # 📊 METRICS
        # =========================
        mttr = last_mttr

        failure_rate = (
            failure_count / total_requests
            if total_requests else 0
        )

        # =========================
        # 🎯 DECISION
        # =========================
        if status == "RED":

            decision = "🚨 Immediate Action Required"

        elif status == "ORANGE":

            decision = "⚠️ Monitor System"

        elif status == "GREEN" and not failure_active:

            decision = "✅ System Stable"

        # =========================
        # 📊 ACCURACY + CM
        # =========================
        if len(y_true) > 10:

            accuracy = accuracy_score(y_true, y_pred)

            cm = confusion_matrix(y_true, y_pred)

            cm_data = cm.tolist()

        # =========================
        # 📝 LOGGING
        # =========================
        log_data(
            temperature,
            humidity,
            failure,
            status,
            mttr
        )

    return render_template(
        'index.html',
        temperature=temperature,
        humidity=humidity,
        failure=failure,
        status=status,
        decision=decision,
        mttr=round(mttr, 2),
        failure_rate=round(failure_rate, 2),
        accuracy=round(accuracy, 2),
        cm_data=cm_data
    )

# =========================
# RUN
# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
