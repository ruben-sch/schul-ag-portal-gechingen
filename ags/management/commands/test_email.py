from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import sys

class Command(BaseCommand):
    help = 'Sends a test email to validate SMTP settings in dev and prod environments'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='The destination email address to send the test message to')

    def handle(self, *args, **kwargs):
        recipient = kwargs['email']
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        
        self.stdout.write(self.style.WARNING(f"Attempting to send an email to {recipient} using SMTP backend: {settings.EMAIL_BACKEND}"))
        self.stdout.write(self.style.WARNING(f"From address: {from_email}\n"))
        
        try:
            send_mail(
                subject='[AG-Portal] SMTP Configuration Test',
                message=f'This is an automated test email from the AG-Portal system.\n\nIf you are reading this, your Django SMTP settings are correctly configured for both your application and your cron/management tasks.\n\nCheers,\nThe AG-Portal Team',
                from_email=from_email,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"Success! The test email has been sent successfully to {recipient}."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send email. An error occurred:\n{str(e)}"))
            sys.exit(1)
