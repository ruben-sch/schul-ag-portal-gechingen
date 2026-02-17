import requests
from bs4 import BeautifulSoup
import os
import django
import random
import re

# Django Setup for direct DB access when needed
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from ags.models import AG, Anmeldung, SchuelerProfile, AppConfig
from django.contrib.auth.models import User
import sesame.utils

BASE_URL = "http://localhost:8000"

def get_csrf(session, url):
    res = session.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')
    token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
    return token['value'] if token else None

def test_full_workflow():
    session = requests.Session()
    print("\n🚀 STARTING FULL E2E WORKFLOW TEST")

    # 1. USE CASE: AG ANLEGEN
    print("\n--- 1. Use Case: AG anlegen ---")
    csrf = get_csrf(session, f"{BASE_URL}/propose/")
    ag_data = {
        'csrfmiddlewaretoken': csrf,
        'name': "Roboter AG",
        'beschreibung': "Wir bauen kleine Roboter.",
        'kosten': 15.00,
        'klassenstufe_min': 3,
        'klassenstufe_max': 4,
        'kapazitaet': 2,
        'termine': "Mittwoch 15:00",
        'verantwortlicher_name': "Herr Technik",
        'verantwortlicher_email': "technik@schule.de",
        'verantwortlicher_telefon': "0151-111111"
    }
    res = session.post(f"{BASE_URL}/propose/", data=ag_data)
    assert res.status_code == 200 and "Vielen Dank" in res.text
    print("✅ AG erfolgreich eingereicht.")

    # Internal: Approve AG and open registration
    ag = AG.objects.get(name="Roboter AG")
    ag.status = 'APPROVED'
    ag.save()
    AppConfig.objects.all().update(anmeldung_offen=True)
    print("✅ AG intern genehmigt und Anmeldung geöffnet.")

    # 2. USE CASE: ANMELDUNG EINES SCHÜLERS
    print("\n--- 2. Use Case: Anmeldung Schueler ---")
    s_email = "paul@test.de"
    csrf_reg = get_csrf(session, f"{BASE_URL}/register/")
    reg_data = {
        'csrfmiddlewaretoken': csrf_reg,
        'name': "Paul Panther",
        'email': s_email,
        'klassenstufe': 4,
        'notfall_telefon': "0170-9876543"
    }
    res_reg = session.post(f"{BASE_URL}/register/", data=reg_data, allow_redirects=True)
    assert "Verfügbare AGs" in res_reg.text
    
    # Select our AG
    soup = BeautifulSoup(res_reg.text, 'html.parser')
    csrf_sel = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
    sel_data = {
        'csrfmiddlewaretoken': csrf_sel,
        'ags': [ag.id]
    }
    res_sel = session.post(f"{BASE_URL}/register/select/", data=sel_data, allow_redirects=True)
    assert "erfolgreich" in res_sel.text
    print("✅ Schüler 'Paul' erfolgreich angemeldet.")

    # 3. USE CASE: AUSLOSUNG
    print("\n--- 3. Use Case: Auslosung ---")
    # Trigger lottery via utility
    from ags.utils import run_lottery
    run_lottery()
    
    anm = Anmeldung.objects.get(schueler__email=s_email, ag=ag)
    assert anm.status == 'ACCEPTED'
    print(f"✅ Auslosung durchgeführt. Pauls Status: {anm.status}")

    # 4. USE CASE: MAGIC LINK SCHÜLER
    print("\n--- 4. Use Case: Magic Link Schueler ---")
    user_s = User.objects.get(email=s_email)
    link_s = f"{BASE_URL}/dashboard/{sesame.utils.get_query_string(user_s)}"
    res_s = session.get(link_s)
    assert "Willkommen, Paul" in res_s.text
    assert "Roboter AG" in res_s.text
    assert "Zugelassen" in res_s.text
    print("✅ Schüler Dashboard via Magic Link verifiziert.")

    # 5. USE CASE: MAGIC LINK LEITER
    print("\n--- 5. Use Case: Magic Link Leiter ---")
    user_l = User.objects.get(email="technik@schule.de")
    link_l = f"{BASE_URL}/dashboard/{sesame.utils.get_query_string(user_l)}"
    res_l = session.get(link_l)
    assert "Deine AG-Verwaltung" in res_l.text
    assert "Roboter AG" in res_l.text
    assert "Paul Panther" in res_l.text
    assert "0170-9876543" in res_l.text
    assert "paul@test.de" in res_l.text
    print("✅ Leiter Dashboard via Magic Link verifiziert (inkl. Teilnehmerdaten).")

    print("\n🏆 ALL USE CASES VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    # Ensure a clean state for the test
    Anmeldung.objects.all().delete()
    AG.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()
    test_full_workflow()
