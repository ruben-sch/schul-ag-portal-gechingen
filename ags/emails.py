from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Anmeldung, AG, SchuelerProfile
from collections import defaultdict

def send_allocation_emails():
    """
    Sends grouped emails to students and detailed lists to leaders.
    """
    # 1. Group emails to Students (only those with ACCEPTED status)
    accepted_anmeldungen = Anmeldung.objects.filter(status='ACCEPTED').select_related('schueler__user', 'ag')
    student_allocations = defaultdict(list)
    
    for anm in accepted_anmeldungen:
        student_allocations[anm.schueler].append(anm.ag)

    for schueler, ag_list in student_allocations.items():
        subject = "Zusagen für deine AG-Anmeldungen"
        context = {
            'schueler': schueler,
            'ag_list': ag_list,
        }
        html_message = render_to_string('ags/emails/acceptance.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [schueler.user.email],
            html_message=html_message,
        )

    # 2. Detailed emails to Leaders (Participants + Waitlist)
    ags = AG.objects.filter(status='APPROVED')
    for ag in ags:
        # Get participants (ACCEPTED)
        participants = Anmeldung.objects.filter(
            ag=ag, status='ACCEPTED'
        ).select_related('schueler__user').order_by('schueler__name')
        
        # Get waitlist (REJECTED/Warteliste)
        waitlist = Anmeldung.objects.filter(
            ag=ag, status='REJECTED'
        ).select_related('schueler__user').order_by('prio', 'erstellt_am')

        if participants.exists() or waitlist.exists():
            subject = f"Teilnehmerliste & Warteliste für AG: {ag.name}"
            context = {
                'ag': ag,
                'participants': participants,
                'waitlist': waitlist,
            }
            html_message = render_to_string('ags/emails/leader_list.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [ag.verantwortlicher_email],
                html_message=html_message,
            )
