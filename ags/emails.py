import csv
import io
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Anmeldung, AG, SchuelerProfile
from collections import defaultdict

def generate_abrechnungsvordruck(ag):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Abrechnungsvordruck", f"AG: {ag.name}"])
    writer.writerow([])
    writer.writerow(["Beschreibung", "Betrag (€)"])
    writer.writerow(["Einnahmen Teilnehmergebühren", ""])
    writer.writerow(["Ausgaben", ""])
    writer.writerow(["Ausgaben", ""])
    writer.writerow(["Ausgaben", ""])
    writer.writerow(["Ausgaben", ""])
    writer.writerow(["Ausgaben", ""])
    writer.writerow(["Summe", ""])
    return output.getvalue().encode('utf-8')

def send_allocation_emails():
    """
    Sends grouped emails to students and detailed lists to leaders.
    """
    # 1. Group emails to Students (only those with ACCEPTED status)
    accepted_anmeldungen = Anmeldung.objects.filter(status=Anmeldung.Status.ACCEPTED).select_related('schueler__user', 'ag')
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
    ags = AG.objects.filter(status=AG.Status.APPROVED)
    for ag in ags:
        # Get participants (ACCEPTED)
        participants = Anmeldung.objects.filter(
            ag=ag, status=Anmeldung.Status.ACCEPTED
        ).select_related('schueler__user').order_by('schueler__name')
        
        # Get waitlist (REJECTED/Warteliste)
        waitlist = Anmeldung.objects.filter(
            ag=ag, status=Anmeldung.Status.REJECTED
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
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[ag.verantwortlicher_email]
            )
            msg.attach_alternative(html_message, "text/html")
            
            csv_content = generate_abrechnungsvordruck(ag)
            msg.attach(f"Abrechnung_{ag.name}.csv", csv_content, "text/csv")
            
            msg.send()
