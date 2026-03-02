import copy
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Anmeldung, AG, SchuelerProfile
from collections import defaultdict

def generate_abrechnungsvordruck(ag):
    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, "Abrechnungsvordruck")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, 780, f"AG: {ag.name}")
    
    c.drawString(50, 740, "Beschreibung")
    c.drawString(400, 740, "Betrag (€)")
    c.line(50, 735, 500, 735)
    
    c.drawString(50, 715, "Einnahmen Teilnehmergebühren")
    c.line(400, 715, 500, 715)
    
    y = 680
    for i in range(5):
        c.drawString(50, y, "Ausgaben")
        c.line(400, y, 500, y)
        y -= 25
        
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y-10, "Summe")
    c.line(400, y-10, 500, y-10)
    
    c.showPage()
    c.save()
    return output.getvalue()

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
            
            pdf_content = generate_abrechnungsvordruck(ag)
            msg.attach(f"Abrechnung_{ag.name}.pdf", pdf_content, "application/pdf")
            
            msg.send()
