import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from ags.models import AppConfig, AG

def seed():
    # 1. Create superuser
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("Superuser 'admin' created (admin123)")

    # 2. Create initial config
    if not AppConfig.objects.exists():
        AppConfig.objects.create(anmeldung_offen=True)
        print("Global config created (Anmeldung is OPEN)")

    # 3. Create some sample AGs
    if not AG.objects.exists():
        AG.objects.create(
            name="Fußball AG",
            beschreibung="Kicken mit Profis.",
            kosten=0,
            klassenstufe_min=1,
            klassenstufe_max=2,
            kapazitaet=20,
            termine=[{'datum': '2026-03-03', 'start': '14:00', 'ende': '15:30'}],
            ort="Turnhalle",
            mitzubringen="Sportzeug",
            verantwortlicher_name="Herr Schmidt",
            verantwortlicher_email="schmidt@schule.de",
            status='APPROVED'
        )
        AG.objects.create(
            name="Coding AG",
            beschreibung="Learn Python and Django.",
            kosten=5,
            klassenstufe_min=3,
            klassenstufe_max=4,
            kapazitaet=15,
            termine=[{'datum': '2026-03-04', 'start': '15:30', 'ende': '17:00'}],
            ort="Computerraum",
            mitzubringen="Stick & gute Laune",
            verantwortlicher_name="Fr. Tech",
            verantwortlicher_email="tech@schule.de",
            status='APPROVED'
        )
        print("Sample AGs created.")

if __name__ == '__main__':
    seed()
