from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Anmeldung, AG

def send_allocation_emails():
    """
    Sends emails to students and leaders after the lottery.
    """
    # 1. Emails to Students
    accepted_anmeldungen = Anmeldung.objects.filter(status='ACCEPTED').select_related('schueler', 'ag')
    for anm in accepted_anmeldungen:
        subject = f"Zusage: Dein Platz in der AG {anm.ag.name}"
        context = {'user': anm.schueler, 'ag': anm.ag}
        html_message = render_to_string('ags/emails/acceptance.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [anm.schueler.email],
            html_message=html_message,
        )

    # 2. Emails to Leaders (Participant list)
    ags = AG.objects.filter(status='APPROVED')
    for ag in ags:
        participants = Anmeldung.objects.filter(ag=ag, status='ACCEPTED').select_related('schueler')
        if participants.exists():
            subject = f"Teilnehmerliste für deine AG: {ag.name}"
            context = {'ag': ag, 'participants': participants}
            html_message = render_to_string('ags/emails/leader_list.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [ag.verantwortlicher_email],
                html_message=html_message,
            )
