import pandas as pd
from flask import Flask, render_template, request
from datetime import datetime, timedelta
import random

app = Flask(__name__)
file_path = 'scalony_plik.csv'

def load_schedule(file_path):
    df = pd.read_csv(file_path, header=None, skiprows=2)
    date_column_index = 1
    group_column_index = 2
    df = df.dropna(subset=[group_column_index])
    df = df[df.iloc[:, group_column_index].astype(str).str.strip() != '']
    df.iloc[:, date_column_index] = pd.to_datetime(df.iloc[:, date_column_index], errors='coerce')
    df = df.dropna(subset=[date_column_index])
    df = df[df.iloc[:, date_column_index].apply(lambda x: isinstance(x, pd.Timestamp))]
    return df

schedule = load_schedule(file_path)

def get_current_week(schedule_df):
    date_series = schedule_df.iloc[:, 1]
    date_series = date_series[date_series.apply(lambda x: isinstance(x, pd.Timestamp))]
    date_series = date_series.dropna()
    
    if date_series.empty:
        return None, None
    
    today = datetime.now()
    earliest_date = today - timedelta(days=today.weekday()) 
    earliest_date = earliest_date.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = earliest_date - timedelta(days=earliest_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week, end_of_week

def minutes_to_time(minutes):
    hours = minutes // 60
    mins = minutes % 60
    return f"{int(hours):02d}:{int(mins):02d}"

def determine_gradient_class(subject):
    if " w1" in subject.lower():
        return "accent-blue-gradient"
    elif " w2" in subject.lower():
        return "accent-blue-gradient"
    elif "sem" in subject.lower():
        return "accent-cyan-gradient"
    elif "sala" in subject.lower():
        return "accent-green-gradient"    
    else:
        return "accent-orange-gradient"

def process_schedule_data(df, group_number, start_date, end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    group_number = str(group_number).strip()
    
    filtered_df = df[(df.iloc[:, 1] >= start_date) & (df.iloc[:, 1] <= end_date)]
    if filtered_df.empty:
        return None
    
    schedule_entries = []
    current_date = start_date
    week_dates = []
    while current_date <= end_date:
        week_dates.append(current_date)
        current_date += timedelta(days=1)
    
    base_time_minutes = 7 * 60

    for current_date in week_dates:
        day_df = filtered_df[filtered_df.iloc[:, 1] == current_date]
        if day_df.empty:
            continue
        
        day = day_df.iloc[0, 0]
        group_rows = day_df[day_df.iloc[:, 2].astype(str).str.strip() == group_number]
    
        if group_rows.empty:
            continue
    
        last_end = 390
    
        for idx, row in group_rows.iterrows():
            if row.isnull().all():
                continue
    
            current_subject = None
            start_time = None
            duration = 0
    
            for col_idx in range(7, day_df.shape[1]):
                cell_value = row[col_idx]
    
                if pd.notnull(cell_value):
                    if current_subject is None:
                        current_subject = cell_value
                        start_time = base_time_minutes + (col_idx - 7) * 15 + 15
                        duration = 15
                    elif cell_value == current_subject:
                        duration += 15
                    else:
                        spacing_before = max(0, start_time - last_end)
                        schedule_entries.append({
                            'date': current_date.date(),
                            'day': day,
                            'subject': current_subject,
                            'start_time': start_time,
                            'duration': duration,
                            'start_time_formatted': minutes_to_time(start_time),
                            'end_time_formatted': minutes_to_time(start_time + duration),
                            'spacing_before': spacing_before,
                            'gradient_class': determine_gradient_class(current_subject)
                        })
                        last_end = start_time + duration
                        current_subject = cell_value
                        start_time = base_time_minutes + (col_idx - 7) * 15 + 15
                        duration = 15
                else:
                    if current_subject is not None:
                        spacing_before = max(0, start_time - last_end)
                        schedule_entries.append({
                            'date': current_date.date(),
                            'day': day,
                            'subject': current_subject,
                            'start_time': start_time,
                            'duration': duration,
                            'start_time_formatted': minutes_to_time(start_time),
                            'end_time_formatted': minutes_to_time(start_time + duration),
                            'spacing_before': spacing_before,
                            'gradient_class': determine_gradient_class(current_subject)
                        })
                        last_end = start_time + duration
                        current_subject = None
                        start_time = None
                        duration = 0
    
            if current_subject is not None:
                spacing_before = max(0, start_time - last_end)
                schedule_entries.append({
                    'date': current_date.date(),
                    'day': day,
                    'subject': current_subject,
                    'start_time': start_time,
                    'duration': duration,
                    'start_time_formatted': minutes_to_time(start_time),
                    'end_time_formatted': minutes_to_time(start_time + duration),
                    'spacing_before': spacing_before,
                    'gradient_class': determine_gradient_class(current_subject)
                })
                last_end = start_time + duration
    
    return schedule_entries

from datetime import datetime, timedelta

@app.route('/', methods=['GET', 'POST'])
def index():
    group_number = '7'
    current_start_date, current_end_date = get_current_week(schedule)

    if current_start_date is None or current_end_date is None:
        return render_template('index.html', schedule_entries=None, group_number=group_number,
                               start_date='', end_date='', error_message="Brak dostępnych dat w harmonogramie.")

    if request.method == 'POST':
        group_number = request.form.get('group_number', '7')
        current_start_date = pd.to_datetime(request.form.get('start_date'))
        current_end_date = pd.to_datetime(request.form.get('end_date'))

        if 'previous_week' in request.form:
            current_start_date -= timedelta(weeks=1)
            current_end_date -= timedelta(weeks=1)
        elif 'next_week' in request.form:
            current_start_date += timedelta(weeks=1)
            current_end_date += timedelta(weeks=1)

    schedule_entries = process_schedule_data(schedule, group_number, current_start_date, current_end_date)
    print(f"Start date: {current_start_date}, type: {type(current_start_date)}")
    return render_template('index.html', schedule_entries=schedule_entries, group_number=group_number,
                           start_date=current_start_date, end_date=current_end_date, error_message=None, timedelta=timedelta)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
