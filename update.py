import requests
from bs4 import BeautifulSoup
import os
import pandas as pd
from openpyxl import load_workbook
from sqlalchemy import create_engine
from datetime import datetime

FILE_PATH = 'plan_downloaded.xlsx'
DB_URL = 'sqlite:///plan.db'
TABLE_NAME = 'schedule_entries'
CHECK_URL = 'https://www.ur.edu.pl/pl/kolegia/kolegium-nauk-medycznych/student/kierunki-studiow1/lekarski/rozklady-zajec'

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

def load_and_process_data(file_path):
    # Wczytanie pliku Excel
    workbook = load_workbook(file_path)
    sheet = workbook.active
    
    data = []
    for row in sheet.iter_rows(values_only=True):
        new_row = []
        for cell in row:
            new_row.append(cell if cell is not None else '')
        data.append(new_row)
    
    df = pd.DataFrame(data)

    # Uzupełnienie scalonych komórek
    merged_cells = sheet.merged_cells.ranges
    for merged_range in merged_cells:
        min_col, min_row, max_col, max_row = merged_range.bounds
        base_value = sheet.cell(row=min_row, column=min_col).value
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                df.iloc[r-1, c-1] = base_value

    # Konwersja dat
    df.iloc[:, 1] = pd.to_datetime(df.iloc[:, 1], format='%d/%m/%Y', errors='coerce')
    df = df.dropna(subset=[df.columns[1]])

    # Usuwamy wiersze, jeśli numer grupy nie jest liczbą z przedziału 1 do 23
    def is_valid_group(group):
        try:
            group_number = int(group)
            return 1 <= group_number <= 23
        except ValueError:
            return False

    df = df[df.iloc[:, 2].apply(is_valid_group)]

    base_time_minutes = 7 * 60  # Start 7:00
    all_entries = []
    unique_dates = df.iloc[:, 1].dropna().unique()
    unique_dates = pd.to_datetime(unique_dates)

    for current_date in unique_dates:
        day_df = df[df.iloc[:, 1] == current_date]
        if day_df.empty:
            continue
        
        day = day_df.iloc[0, 0]
        groups = day_df.iloc[:, 2].unique()

        for group_number in groups:
            group_rows = day_df[day_df.iloc[:, 2] == group_number]
            if group_rows.empty:
                continue
            
            last_end = base_time_minutes
            for _, row in group_rows.iterrows():
                current_subject = None
                start_time = None
                duration = 0

                for col_idx in range(6, len(row)):
                    cell_value = row[col_idx]
                    slot_start_minutes = base_time_minutes + (col_idx - 6) * 15

                    if pd.notnull(cell_value) and cell_value != '':
                        if current_subject is None:
                            current_subject = cell_value
                            start_time = slot_start_minutes
                            duration = 15
                        elif cell_value == current_subject:
                            duration += 15
                        else:
                            spacing_before = max(0, start_time - last_end)
                            all_entries.append({
                                'date': current_date.date(),
                                'day': day,
                                'group_number': str(group_number),
                                'subject': current_subject,
                                'start_time_formatted': f"{start_time//60:02d}:{start_time%60:02d}",
                                'end_time_formatted': f"{(start_time+duration)//60:02d}:{(start_time+duration)%60:02d}",
                                'duration': duration,
                                'spacing_before': spacing_before,
                                'gradient_class': determine_gradient_class(str(current_subject))
                            })
                            last_end = start_time + duration
                            current_subject = cell_value
                            start_time = slot_start_minutes
                            duration = 15
                    else:
                        if current_subject is not None:
                            spacing_before = max(0, start_time - last_end)
                            all_entries.append({
                                'date': current_date.date(),
                                'day': day,
                                'group_number': str(group_number),
                                'subject': current_subject,
                                'start_time_formatted': f"{start_time//60:02d}:{start_time%60:02d}",
                                'end_time_formatted': f"{(start_time+duration)//60:02d}:{(start_time+duration)%60:02d}",
                                'duration': duration,
                                'spacing_before': spacing_before,
                                'gradient_class': determine_gradient_class(str(current_subject))
                            })
                            last_end = start_time + duration
                            current_subject = None
                            start_time = None
                            duration = 0

                if current_subject is not None:
                    spacing_before = max(0, start_time - last_end)
                    all_entries.append({
                        'date': current_date.date(),
                        'day': day,
                        'group_number': str(group_number),
                        'subject': current_subject,
                        'start_time_formatted': f"{start_time//60:02d}:{start_time%60:02d}",
                        'end_time_formatted': f"{(start_time+duration)//60:02d}:{(start_time+duration)%60:02d}",
                        'duration': duration,
                        'spacing_before': spacing_before,
                        'gradient_class': determine_gradient_class(str(current_subject))
                    })

    final_df = pd.DataFrame(all_entries)
    return final_df

def save_to_db(df, db_url, table_name):
    engine = create_engine(db_url)
    df.to_sql(table_name, engine, if_exists='replace', index=False)

def get_last_update_info():
    # Sprawdź w bazie lub pliku ostatnią datę aktualizacji
    # Dla prostoty zakładamy plik z datą aktualizacji: last_update.txt
    if not os.path.exists('last_update.txt'):
        return None, None
    with open('last_update.txt', 'r') as f:
        line = f.readline().strip()
        if line:
            parts = line.split('|')
            if len(parts) == 2:
                return parts[0], parts[1]  # data aktualizacji, url pliku
    return None, None

def set_last_update_info(update_date, url):
    with open('last_update.txt', 'w') as f:
        f.write(f"{update_date}|{url}")

def check_for_new_update():
    # Pobierz stronę i sprawdź aktualizację
    r = requests.get(CHECK_URL)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')

    # Znajdujemy wiersz z "V rok kierunek lekarski"
    # Zakładamy, że jest to określone w tym fragmencie kodu (podobnie jak w przesłanym HTML)
    # Szukamy <td> z tekstem "V rok kierunek lekarski" i pobieramy obok datę i link.
    
    row = None
    all_rows = soup.select('table tr')
    for tr in all_rows:
        tds = tr.find_all('td')
        if len(tds) > 0 and 'V rok kierunek lekarski' in tds[0].get_text() and 'IV rok kierunek lekarski' not in tds[0].get_text():
            row = tds
            break
    
    if not row:
        print("Nie znaleziono wiersza z V rok kierunek lekarski.")
        return

    # W tds[0] mamy nazwę, w tds[1] powinna być data aktualizacji, w tds[0] link
    # Link do pliku XLSX:
    link = row[0].find('a', href=True)['href']
    # Data aktualizacji w tds[1]:
    update_text = row[1].get_text(strip=True)  # np. "aktualizacja 02.12.2024"
    # Wyciągamy datę aktualizacji
    # Zakładamy format: "aktualizacja dd.mm.yyyy"
    # Możemy spróbować np. split po spacji
    parts = update_text.split()
    update_date_str = None
    for p in parts:
        if '.' in p:
            update_date_str = p
            break
    # update_date_str to np. "02.12.2024"
    # możemy ją zapisać jako string w last_update.txt
    # Porównamy z poprzednią aktualizacją
    last_date, last_url = get_last_update_info()
    if last_date != update_date_str or last_url != link:
        # Nowa aktualizacja
        print("Wykryto nowa aktualizacje planu dla V roku.")
        if link.startswith('/'):
            download_url = 'https://www.ur.edu.pl' + link
        else:
            # jeśli z jakiegoś powodu link nie zaczyna się od /
            download_url = 'https://www.ur.edu.pl/' + link


        print(download_url)
        # Pobieramy plik
        x = requests.get(download_url)
        x.raise_for_status()
        with open(FILE_PATH, 'wb') as f:
            f.write(x.content)
        # Przetwarzamy dane
        final_df = load_and_process_data(FILE_PATH)
        save_to_db(final_df, DB_URL, TABLE_NAME)
        set_last_update_info(update_date_str, link)
    else:
        print("Brak nowej aktualizacji dla V roku.")

if __name__ == "__main__":
    try:
        check_for_new_update()
    except Exception as e:
        print(f"Błąd w trakcie aktualizacji: {e}")
        raise