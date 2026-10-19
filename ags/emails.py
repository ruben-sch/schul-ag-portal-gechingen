import io
import os
import logging
import smtplib
import time

logger = logging.getLogger(__name__)
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Anmeldung, AG, SchuelerProfile
from collections import defaultdict

BCC_ADRESSE = 'eltern-ags-sgs@googlegroups.com'
MAX_VERSUCHE = 3


def _ist_voruebergehend(exc):
    """True für Fehler, bei denen ein erneuter Versuch sinnvoll ist (Timeout, Verbindungsabbruch, SMTP 4xx)."""
    if isinstance(exc, (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError)):
        return True
    if isinstance(exc, smtplib.SMTPResponseException):
        return 400 <= exc.smtp_code < 500
    return isinstance(exc, (TimeoutError, ConnectionError))


def _senden(msg):
    """
    Sendet eine Nachricht mit bis zu MAX_VERSUCHE Versuchen und exponentiellem Backoff.
    Dauerhafte Fehler (z.B. SMTP 5xx, ungültiger Empfänger) werden sofort weitergereicht.
    """
    for versuch in range(1, MAX_VERSUCHE + 1):
        try:
            msg.send(fail_silently=False)
            return
        except Exception as exc:
            if versuch == MAX_VERSUCHE or not _ist_voruebergehend(exc):
                raise
            wartezeit = settings.EMAIL_RETRY_DELAY * 2 ** (versuch - 1)
            logger.warning("E-Mail an %s fehlgeschlagen (Versuch %s/%s): %s. Neuer Versuch in %ss.",
                           msg.to, versuch, MAX_VERSUCHE, exc, wartezeit)
            # Eine abgebrochene Verbindung schließen, damit der nächste Versuch neu verbindet.
            if msg.connection is not None:
                try:
                    msg.connection.close()
                except Exception:
                    msg.connection.connection = None
            time.sleep(wartezeit)


def send_registration_confirmation(schueler, anmeldungen=None, connection=None):
    """
    Sends the registration confirmation to a single student.
    Returns True if sent successfully, False otherwise.
    """
    if anmeldungen is None:
        anmeldungen = list(Anmeldung.objects.filter(schueler=schueler).select_related('ag').order_by('prio'))

    context = {'schueler': schueler, 'anmeldungen': anmeldungen}
    html_message = render_to_string('ags/emails/registration_confirmation.html', context)
    msg = EmailMultiAlternatives(
        subject="Deine Schul-AG Anmeldung",
        body=strip_tags(html_message),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[schueler.user.email],
        bcc=[BCC_ADRESSE],
        connection=connection,
    )
    msg.attach_alternative(html_message, "text/html")
    try:
        _senden(msg)
    except Exception as e:
        logger.error("Failed to send confirmation email to %s: %s", schueler.user.email, e)
        schueler.confirmation_email_sent = False
        schueler.save(update_fields=['confirmation_email_sent'])
        return False
    schueler.confirmation_email_sent = True
    schueler.save(update_fields=['confirmation_email_sent'])
    return True

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

def send_single_acceptance_email(schueler, ag_list=None, connection=None):
    """
    Sends the acceptance email to a single student.
    Returns True if sent successfully, False otherwise.
    """
    if ag_list is None:
        accepted_anmeldungen = Anmeldung.objects.filter(schueler=schueler, status=Anmeldung.Status.ACCEPTED).select_related('ag')
        ag_list = [anm.ag for anm in accepted_anmeldungen]

    subject = "Zusagen für deine AG-Anmeldungen"
    context = {
        'schueler': schueler,
        'ag_list': ag_list,
    }
    html_message = render_to_string('ags/emails/acceptance.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[schueler.user.email],
            bcc=[BCC_ADRESSE],
            connection=connection,
        )
        msg.attach_alternative(html_message, "text/html")
        _senden(msg)
        schueler.acceptance_email_sent = True
        schueler.save()
        return True
    except Exception as e:
        logger.error(f"Failed to send acceptance email to {schueler.user.email}: {e}")
        return False

def send_single_leader_email(ag, connection=None):
    """
    Sends the detailed email (participants + waitlist) to the AG leader.
    Returns True if sent successfully, False otherwise.
    """
    # Get participants (ACCEPTED)
    participants = Anmeldung.objects.filter(
        ag=ag, status=Anmeldung.Status.ACCEPTED
    ).select_related('schueler__user').order_by('schueler__name')
    
    # Get waitlist (REJECTED/Warteliste)
    waitlist = Anmeldung.objects.filter(
        ag=ag, status=Anmeldung.Status.REJECTED
    ).select_related('schueler__user').order_by('prio', 'erstellt_am')

    if not participants.exists() and not waitlist.exists():
        return False

    subject = f"Teilnehmerliste & Warteliste für AG: {ag.name}"
    context = {
        'ag': ag,
        'participants': participants,
        'waitlist': waitlist,
    }
    html_message = render_to_string('ags/emails/leader_list.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[ag.verantwortlicher_email],
            bcc=[BCC_ADRESSE],
            connection=connection,
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
        
        _senden(msg)
        ag.leader_email_sent = True
        ag.save()
        return True
    except Exception as e:
        logger.error(f"Failed to send leader email for {ag.name} to {ag.verantwortlicher_email}: {e}")
        return False

def send_allocation_emails(only_unsent=False, send_students=True, send_leaders=True):
    """
    Sends grouped emails to students and detailed lists to leaders.
    Returns a dict with sent/failed counts for students and leaders.
    """
    results = {'students_sent': 0, 'students_failed': 0, 'leaders_sent': 0, 'leaders_failed': 0}
    # Eine SMTP-Verbindung für den ganzen Lauf statt einer pro Mail.
    connection = get_connection()
    try:
        _send_allocation_emails(connection, results, only_unsent, send_students, send_leaders)
    finally:
        connection.close()
    return results


def _send_allocation_emails(connection, results, only_unsent, send_students, send_leaders):

    # 1. Group emails to Students (only those with ACCEPTED status)
    if send_students:
        accepted_anmeldungen = Anmeldung.objects.filter(status=Anmeldung.Status.ACCEPTED).select_related('schueler__user', 'ag')
        student_allocations = defaultdict(list)
        
        for anm in accepted_anmeldungen:
            if only_unsent and anm.schueler.acceptance_email_sent:
                continue
            student_allocations[anm.schueler].append(anm.ag)

        for schueler, ag_list in student_allocations.items():
            success = send_single_acceptance_email(schueler, ag_list, connection=connection)
            if success:
                results['students_sent'] += 1
            else:
                results['students_failed'] += 1

    # 2. Detailed emails to Leaders (Participants + Waitlist)
    if send_leaders:
        ags = AG.objects.filter(status=AG.Status.APPROVED)
        for ag in ags:
            if only_unsent and ag.leader_email_sent:
                continue
            success = send_single_leader_email(ag, connection=connection)
            if success:
                results['leaders_sent'] += 1
            else:
                results['leaders_failed'] += 1
