import subprocess
import pandas as pd
from sqlalchemy import create_engine
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from google_event import add_event
from flask import send_file, jsonify
from weasyprint import HTML, CSS
from pdf2image import convert_from_path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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


def get_rendered_html(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,3000")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    html_source = driver.page_source
    driver.quit()
    return html_source


@app.route('/save-schedule-to-image', methods=['GET'])
def save_schedule_to_image():
    url = "http://localhost:5000"
    output_pdf_path = "schedule.pdf"
    html_content = get_rendered_html(url)

    HTML(string=html_content).write_pdf(output_pdf_path, stylesheets=[
        CSS(string='@page { size: A4 landscape; margin: 1cm; }')
    ])
    return jsonify({"status": "success", "image_url": f'/static/{output_pdf_path}'})


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

    # Pobierz datę ostatniej aktualizacji
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
    # Uruchom skrypt update.py
    try:
        result = subprocess.run(["python", "update.py"], capture_output=True, text=True)
        if result.returncode == 0:
            return jsonify({"status": "success", "message": "Update executed successfully.", "output": result.stdout})
        else:
            return jsonify({"status": "error", "message": "Update script failed.", "error": result.stderr}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/update-google-event', methods=['POST'])
def update_google_event():
    try:
        data = request.json
        add_event(data['title'], data['startTime'], data['endTime'], "", "")
        return jsonify({"status": "success", "message": "Event added to Google Calendar successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
