import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ags.models import AG, SchuelerProfile, Anmeldung, AppConfig, ArchivEintrag
from django.core import serializers

class Command(BaseCommand):
    help = 'Archiviert die aktuelle Runde in der Datenbank und setzt das System für das nächste Halbjahr zurück.'

    def handle(self, *args, **options):
        # Aktuelles Halbjahr bestimmen (z.B. 2024_H1)
        now = datetime.now()
        semester_label = f"{now.year}_H{1 if now.month <= 7 else 2}"

        # 1. Sicherung in der Datenbank (UI-Archiv)
        self.stdout.write("Erstelle Datenbank-Archiv...")
        anmeldungen = Anmeldung.objects.select_related('schueler', 'ag').all()
        
        archiv_objekte = [
            ArchivEintrag(
                schueler_name=anm.schueler.name,
                schueler_email=anm.schueler.user.email,
                ag_name=anm.ag.name,
                halbyahr=semester_label,
                status=anm.get_status_display(),
                details={
                    'ag_termin_display': anm.ag.get_termine_display(),
                    'ag_ort': anm.ag.ort,
                    'ag_leiter': anm.ag.verantwortlicher_name,
                    'ag_termine_raw': anm.ag.termine,
                }
            ) for anm in anmeldungen
        ]
        ArchivEintrag.objects.bulk_create(archiv_objekte)
        self.stdout.write(self.style.SUCCESS(f"{len(archiv_objekte)} Einträge archiviert."))

        # 2. JSON-Sicherung (Zusatz-Backup / Log-Ausgabe)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        archive_dir = 'archives'
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
        
        filename = f"{archive_dir}/semester_backup_{timestamp}.json"
        
        all_data = list(AG.objects.all()) + \
                   list(SchuelerProfile.objects.all()) + \
                   list(Anmeldung.objects.all())
        
        if all_data:
            json_data = serializers.serialize('json', all_data, indent=2)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(json_data)
            self.stdout.write(self.style.SUCCESS(f"JSON-Backup erstellt: {filename}"))
            # Für Cloud-Logs:
            self.stdout.write("--- BEGIN JSON BACKUP ---")
            self.stdout.write(json_data)
            self.stdout.write("--- END JSON BACKUP ---")

        # 3. Zurücksetzen (Löschen)
        self.stdout.write("Setze Datenbank zurück...")
        Anmeldung.objects.all().delete()
        SchuelerProfile.objects.all().delete()
        AG.objects.all().delete()
        
        deleted_users, _ = User.objects.filter(is_superuser=False, is_staff=False).delete()
        AppConfig.objects.all().update(anmeldung_offen=False)
        
        self.stdout.write(self.style.SUCCESS(
            f"Datenbank bereinigt. {deleted_users} Benutzer gelöscht. Bereit für die neue Runde!"
        ))
