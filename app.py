import subprocess
import pandas as pd
from sqlalchemy import create_engine
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import os

DB_URL = 'sqlite:///plan.db'
TABLE_NAME = 'schedule_entries'

app = Flask(__name__)
engine = create_engine(DB_URL)
ENTRIES = []

def get_current_week():
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week, end_of_week

def get_last_update_date():
    try:
        with open('last_update.txt', 'r') as f:
            line = f.readline().strip()
            if line:
                date_part = line.split('|')[0]
                return date_part
    except FileNotFoundError:
        return "Brak danych"
    return "Brak danych"

@app.route('/', methods=['GET', 'POST'])
def index():
    group_number = request.form.get('group_number', '7')
    start_date_str = request.form.get('start_date', None)
    end_date_str = request.form.get('end_date', None)

    if start_date_str and end_date_str:
        current_start_date = pd.to_datetime(start_date_str)
        current_end_date = pd.to_datetime(end_date_str)
    else:
        current_start_date, current_end_date = get_current_week()

    if request.method == 'POST':
        if 'previous_week' in request.form:
            current_start_date -= timedelta(weeks=1)
            current_end_date -= timedelta(weeks=1)
        elif 'next_week' in request.form:
            current_start_date += timedelta(weeks=1)
            current_end_date += timedelta(weeks=1)

    query = f"""
    SELECT * FROM {TABLE_NAME}
    WHERE date >= '{current_start_date.date()}'
      AND date <= '{current_end_date.date()}'
      AND group_number = '{group_number}'
    """

    schedule_entries = pd.read_sql(query, engine)
    schedule_entries['date'] = pd.to_datetime(schedule_entries['date']).dt.date

    if schedule_entries.empty:
        error_message = "Brak zajęć dla wybranej grupy w wybranym tygodniu."
    else:
        error_message = None

    ENTRIES = schedule_entries.to_dict('records')

    for entry_id, entry in enumerate(ENTRIES):
        entry["id"] = entry_id

    last_update_date = get_last_update_date()
    return render_template('index.html',
                           schedule_entries=ENTRIES,
                           group_number=group_number,
                           start_date=current_start_date,
                           end_date=current_end_date,
                           error_message=error_message,
                           last_update_date=last_update_date,
                           timedelta=timedelta)

@app.route('/update', methods=['GET'])
def update_schedule():
    try:
        result = subprocess.run(["python", "update.py"], capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return jsonify({"status": "success", "message": "Update executed successfully.", "output": result.stdout})
        else:
            return jsonify({"status": "error", "message": "Update script failed.", "error": result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "Update script timed out after 5 minutes."}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)