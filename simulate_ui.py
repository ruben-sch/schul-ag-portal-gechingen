import os
import requests
from bs4 import BeautifulSoup
import random
import time

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")

def get_csrf_token(session, url):
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
    if token:
        return token['value']
    return None

def simulate():
    session = requests.Session()
    
    print("--- 1. Proposing 15 AGs ---")
    ag_ids = []
    for i in range(1, 16):
        csrf = get_csrf_token(session, f"{BASE_URL}/propose/")
        data = {
            'csrfmiddlewaretoken': csrf,
            'name': f"Test AG {i}",
            'beschreibung': f"Dies ist eine automatisch generierte Test-AG Nummer {i}.",
            'kosten': random.randint(0, 20),
            'klassenstufe_min': random.randint(1, 2),
            'klassenstufe_max': random.randint(3, 4),
            'kapazitaet': random.randint(5, 10),
            'termine': '[{"datum": "2026-03-02", "start": "14:00", "ende": "15:30"}]',
            'mitzubringen': 'Testausrüstung',
            'hinweise': 'Keine',
            'verantwortlicher_name': f"Leiter {i}",
            'verantwortlicher_email': f"leiter{i}@example.com",
            'verantwortlicher_telefon': "012345678"
        }
        res = session.post(f"{BASE_URL}/propose/", data=data)
        if res.status_code == 200:
            print(f"AG {i} eingereicht.")
        else:
            print(f"Fehler bei AG {i}: {res.status_code}")

    print("\n--- 2. Approving AGs (Internal Script) ---")
    # Instead of simulating admin UI (complex CSRF/Login), we use a helper to approve all
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    from ags.models import AG, AppConfig
    
    AG.objects.all().update(status='APPROVED')
    AppConfig.objects.all().update(anmeldung_offen=True)
    all_ags = list(AG.objects.all())
    print(f"{len(all_ags)} AGs wurden genehmigt.")

    print("\n--- 3. Simulating 100 Students ---")
    for s in range(1, 101):
        student_session = requests.Session()
        email = f"student{s}@test.de"
        klasse = random.randint(1, 4)
        
        # Step 1: Register Personal Data
        csrf1 = get_csrf_token(student_session, f"{BASE_URL}/register/")
        step1_data = {
            'csrfmiddlewaretoken': csrf1,
            'name': f"Schüler_{s}",
            'email': email,
            'klassenstufe': klasse,
            'notfall_telefon': f"0176-{random.randint(1000000, 9999999)}"
        }
        res1 = student_session.post(f"{BASE_URL}/register/", data=step1_data, allow_redirects=True)
        
        if "Verfügbare AGs" in res1.text:
            # Step 2: Select AGs
            soup = BeautifulSoup(res1.text, 'html.parser')
            available_checkboxes = soup.find_all('input', {'name': 'ags'})
            available_ids = [cb['value'] for cb in available_checkboxes]
            
            if available_ids:
                num_to_select = min(len(available_ids), random.randint(3, 5))
                selected_ids = random.sample(available_ids, num_to_select)
                
                csrf2 = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
                step2_data = {
                    'csrfmiddlewaretoken': csrf2,
                    'ags': selected_ids
                }
                res2 = student_session.post(f"{BASE_URL}/register/select/", data=step2_data, allow_redirects=True)
                if res2.status_code == 200:
                    print(f"Student {s} ({email}, Klasse {klasse}) angemeldet für {num_to_select} AGs.")
            else:
                print(f"Student {s}: Keine AGs für Klasse {klasse} verfügbar.")
        else:
            print(f"Student {s}: Fehler bei Schritt 1.")

if __name__ == "__main__":
    # Give the server a moment to be really up if running via shell
    simulate()
