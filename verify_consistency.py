import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from ags.models import AG, Anmeldung, SchuelerProfile

def verify_data():
    print("--- DATA CONSISTENCY CHECK ---")
    all_anmeldungen = Anmeldung.objects.all()
    count = 0
    errors = 0
    for a in all_anmeldungen:
        count += 1
        p = a.schueler.schueler_profile
        if p.klassenstufe < a.ag.klassenstufe_min or p.klassenstufe > a.ag.klassenstufe_max:
            errors += 1
            print(f"FAILED: {a.schueler.email} (Grade {p.klassenstufe}) registered for {a.ag.name} (Valid: {a.ag.klassenstufe_min}-{a.ag.klassenstufe_max})")
    
    if errors == 0:
        print(f"SUCCESS: All {count} registrations match grade levels!")
    else:
        print(f"FINISHED: Found {errors} errors in {count} registrations.")

if __name__ == '__main__':
    verify_data()
