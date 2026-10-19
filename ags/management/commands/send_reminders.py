from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from ags.emails import send_termin_reminders


class Command(BaseCommand):
    help = 'Verschickt Erinnerungsmails an Teilnehmer für anstehende AG-Termine (idempotent, stündlich ausführbar).'

    def add_arguments(self, parser):
        parser.add_argument('--sofort', action='store_true', help='Uhrzeit-Sperre (REMINDER_EARLIEST_HOUR) ignorieren')

    def handle(self, *args, **options):
        if not options['sofort'] and timezone.localtime().hour < settings.REMINDER_EARLIEST_HOUR:
            self.stdout.write(f"Vor {settings.REMINDER_EARLIEST_HOUR} Uhr werden keine Erinnerungen verschickt.")
            return
        results = send_termin_reminders()
        self.stdout.write(f"Erinnerungen: {results['sent']} gesendet, {results['failed']} fehlgeschlagen.")
        if results['abgebrochen']:
            self.stdout.write("Lauf wegen eines vorübergehenden SMTP-Fehlers abgebrochen; der nächste Lauf holt den Rest nach.")
