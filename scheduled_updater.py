import requests
import schedule
import time
import os
import logging
from datetime import datetime

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scheduler.log')
    ]
)
logger = logging.getLogger(__name__)

def run_update():
    try:
        # URL twojej aplikacji na Render.com
        app_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://your-app-name.onrender.com')
        update_url = f"{app_url}/update"
        
        logger.info(f"Rozpoczynam aktualizację planu: {update_url}")
        
        # Wysyłamy request do endpointu /update
        response = requests.get(update_url, timeout=300)  # 5 minut timeout
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Aktualizacja zakończona sukcesem: {result.get('message', 'Brak wiadomości')}")
            if 'output' in result and result['output']:
                logger.info(f"Output: {result['output']}")
        else:
            logger.error(f"Aktualizacja nie powiodła się. Status: {response.status_code}")
            try:
                error_details = response.json()
                logger.error(f"Szczegóły błędu: {error_details}")
            except:
                logger.error(f"Response text: {response.text}")
            
    except requests.exceptions.Timeout:
        logger.error("Aktualizacja przekroczyła limit czasu (5 minut)")
    except requests.exceptions.RequestException as e:
        logger.error(f"Błąd podczas wykonywania requestu: {str(e)}")
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd: {str(e)}")

# Zaplanuj zadania
def schedule_updates():
    # Codziennie o północy
    schedule.every().day.at("00:00").do(run_update)
    
    # Dodatkowo co 6 godzin dla testów (możesz usunąć w produkcji)
    schedule.every(6).hours.do(run_update)
    
    logger.info("Harmonogram zadań został ustawiony")
    logger.info("Aktualizacje będą wykonywane codziennie o 00:00 i co 6 godzin")

if __name__ == "__main__":
    logger.info("Uruchamiam scheduled updater...")
    
    # Sprawdź czy jesteśmy na Render.com
    if os.environ.get('RENDER'):
        logger.info("Środowisko: Render.com")
    else:
        logger.info("Środowisko: Lokalne")
    
    schedule_updates()
    
    # Uruchom pierwszą aktualizację przy starcie (z opóźnieniem 30s aby aplikacja zdążyła się uruchomić)
    logger.info("Uruchamiam pierwszą aktualizację za 30 sekund...")
    time.sleep(30)
    run_update()
    
    logger.info("Scheduler działa. Sprawdzanie zaplanowanych zadań co minutę...")
    
    # Główna pętla
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Sprawdzaj co minutę
        except Exception as e:
            logger.error(f"Błąd w głównej pętli schedulera: {str(e)}")
            time.sleep(60)