import copy
import io
import os
import logging

logger = logging.getLogger(__name__)
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Anmeldung, AG, SchuelerProfile
from collections import defaultdict

def draw_header(c, title, ag_name):
    # Logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo_sgs.png')
    if os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            c.drawImage(img, 400, 760, width=140, height=140 * 156 / 340, preserveAspectRatio=True)
        except Exception as e:
            logger.warning("Error drawing logo: %s", e)
            
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 800, "Schlehengäuschule Gechingen")
    c.setFont("Helvetica", 10)
    c.drawString(50, 785, "AG-Portal")
    
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 740, title)
    
    c.setFont("Helvetica", 12)
    c.drawString(50, 715, f"AG: {ag_name}")

def generate_abrechnungsvordruck(ag):
    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=A4)
    draw_header(c, "Abrechnungsvordruck", ag.name)
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 680, "Beschreibung")
    c.drawString(400, 680, "Betrag (€)")
    c.line(50, 675, 500, 675)
    
    c.setFont("Helvetica", 12)
    c.drawString(50, 650, "Einnahmen Teilnehmergebühren")
    c.line(400, 650, 500, 650)
    
    y = 615
    for i in range(5):
        c.drawString(50, y, "Ausgaben " + "." * 70)
        c.line(400, y, 500, y)
        y -= 30
        
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y-10, "Summe")
    c.line(400, y-10, 500, y-10)
    
    c.showPage()
    c.save()
    return output.getvalue()

def generate_student_list_pdf(ag, students, title):
    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=A4)
    draw_header(c, title, ag.name)
    
    y = 670
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Prio")
    c.drawString(100, y, "Name")
    c.drawString(300, y, "Klasse")
    c.drawString(400, y, "Notfall-Telefon")
    c.line(50, y-5, 530, y-5)
    
    y -= 25
    c.setFont("Helvetica", 11)
    
    for anm in students:
        if y < 50:
            c.showPage()
            draw_header(c, title + " (Fortsetzung)", ag.name)
            y = 680
            c.setFont("Helvetica", 11)
            
        profile = anm.schueler
        c.drawString(50, y, str(anm.prio))
        c.drawString(100, y, str(profile.name))
        c.drawString(300, y, f"Klasse {profile.klassenstufe}")
        c.drawString(400, y, str(profile.notfall_telefon))
        c.line(50, y-5, 530, y-5)
        y -= 20
        
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
            
            if participants.exists():
                tl_pdf = generate_student_list_pdf(ag, participants, "Teilnehmerliste")
                msg.attach(f"Teilnehmerliste_{ag.name}.pdf", tl_pdf, "application/pdf")
                
            if waitlist.exists():
                wl_pdf = generate_student_list_pdf(ag, waitlist, "Warteliste")
                msg.attach(f"Warteliste_{ag.name}.pdf", wl_pdf, "application/pdf")
            
            msg.send()
