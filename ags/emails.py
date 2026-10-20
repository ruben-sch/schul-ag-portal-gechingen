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


def _ist_abgelehnt(exc):
    """True, wenn der Server die Nachricht ausdrücklich vorübergehend abgelehnt hat (SMTP 4xx), sie also nicht zugestellt ist."""
    return isinstance(exc, smtplib.SMTPResponseException) and 400 <= exc.smtp_code < 500


def _verbindung_oeffnen(connection):
    """
    Stellt sicher, dass die Verbindung offen ist, und baut eine vom Server getrennte Verbindung neu auf.
    Fehler hier passieren vor dem Senden und können gefahrlos wiederholt werden.
    """
    smtp = getattr(connection, 'connection', None)
    if smtp is not None:
        try:
            if smtp.noop()[0] == 250:
                return
        except Exception:
            pass
        try:
            connection.close()
        except Exception:
            connection.connection = None
    connection.open()


def _senden(msg):
    """
    Sendet eine Nachricht mit bis zu MAX_VERSUCHE Versuchen und exponentiellem Backoff.

    Wiederholt wird nur, wenn die Nachricht sicher nicht zugestellt wurde: beim Verbindungsaufbau
    oder wenn der Server sie mit SMTP 4xx ablehnt. Ein Timeout oder Abbruch während des Sendens
    wird nicht wiederholt, weil der Server die Mail schon angenommen haben kann (sonst käme sie doppelt an).
    Eine übergebene Verbindung bleibt offen, damit ein Bulk-Lauf sie weiterverwenden kann.
    """
    eigene_verbindung = msg.connection is None
    connection = msg.connection or get_connection()
    try:
        for versuch in range(1, MAX_VERSUCHE + 1):
            try:
                _verbindung_oeffnen(connection)
            except Exception as exc:
                if versuch == MAX_VERSUCHE or not _ist_voruebergehend(exc):
                    raise
                _warten(msg, versuch, exc)
                continue
            try:
                connection.send_messages([msg])
                return
            except Exception as exc:
                if versuch == MAX_VERSUCHE or not _ist_abgelehnt(exc):
                    raise
                _warten(msg, versuch, exc)
    finally:
        if eigene_verbindung:
            connection.close()


def _warten(msg, versuch, exc):
    wartezeit = settings.EMAIL_RETRY_DELAY * 2 ** (versuch - 1)
    logger.warning("E-Mail an %s fehlgeschlagen (Versuch %s/%s): %s. Neuer Versuch in %ss.",
                   msg.to, versuch, MAX_VERSUCHE, exc, wartezeit)
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
        # Nur das Flag schreiben: Ein Bulk-Lauf hält das Objekt lange, Änderungen der Eltern sollen erhalten bleiben.
        schueler.save(update_fields=['acceptance_email_sent'])
        return True
    except Exception as e:
        logger.error(f"Failed to send acceptance email to {schueler.user.email}: {e}")
        return False

def send_single_leader_email(ag, connection=None):
    """
    Sends the detailed email (participants + waitlist) to the AG leader.
    Returns True if sent successfully, False on error and None if the AG has no registrations.
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
        return None

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
        ag.save(update_fields=['leader_email_sent'])
        return True
    except Exception as e:
        logger.error(f"Failed to send leader email for {ag.name} to {ag.verantwortlicher_email}: {e}")
        return False

def offene_zusagen(only_unsent=False):
    """IDs der Schüler mit mindestens einer Zusage, optional nur die noch ohne Zuteilungsmail."""
    qs = SchuelerProfile.objects.filter(anmeldungen__status=Anmeldung.Status.ACCEPTED)
    if only_unsent:
        qs = qs.filter(acceptance_email_sent=False)
    return list(qs.distinct().order_by('id').values_list('id', flat=True))


def offene_leiter_mails(only_unsent=False):
    """IDs der genehmigten AGs, optional nur die noch ohne Leiter-Mail."""
    qs = AG.objects.filter(status=AG.Status.APPROVED)
    if only_unsent:
        qs = qs.filter(leader_email_sent=False)
    return list(qs.order_by('id').values_list('id', flat=True))


def send_acceptance_emails(schueler_ids, only_unsent=False, connection=None):
    """Sendet die Zuteilungsmails an die angegebenen Schüler. Gibt (gesendet, fehlgeschlagen) zurück."""
    anmeldungen = Anmeldung.objects.filter(
        schueler_id__in=schueler_ids, status=Anmeldung.Status.ACCEPTED
    ).select_related('schueler__user', 'ag')
    if only_unsent:
        anmeldungen = anmeldungen.filter(schueler__acceptance_email_sent=False)
    zuteilungen = defaultdict(list)
    for anm in anmeldungen:
        zuteilungen[anm.schueler].append(anm.ag)

    sent = failed = 0
    for schueler, ag_list in zuteilungen.items():
        if send_single_acceptance_email(schueler, ag_list, connection=connection):
            sent += 1
        else:
            failed += 1
    return sent, failed


def send_leader_emails(ag_ids, only_unsent=False, connection=None):
    """Sendet die Teilnehmerlisten an die Leitungen der angegebenen AGs. Gibt (gesendet, fehlgeschlagen) zurück."""
    ags = AG.objects.filter(id__in=ag_ids, status=AG.Status.APPROVED).order_by('id')
    if only_unsent:
        ags = ags.filter(leader_email_sent=False)
    sent = failed = 0
    for ag in ags:
        ergebnis = send_single_leader_email(ag, connection=connection)
        if ergebnis:
            sent += 1
        elif ergebnis is False:
            failed += 1
    return sent, failed


def send_allocation_emails(only_unsent=False, send_students=True, send_leaders=True):
    """
    Sends grouped emails to students and detailed lists to leaders in one run.
    Returns a dict with sent/failed counts for students and leaders.
    """
    results = {'students_sent': 0, 'students_failed': 0, 'leaders_sent': 0, 'leaders_failed': 0}
    # Eine SMTP-Verbindung für den ganzen Lauf statt einer pro Mail.
    connection = get_connection()
    try:
        if send_students:
            results['students_sent'], results['students_failed'] = send_acceptance_emails(
                offene_zusagen(only_unsent), connection=connection)
        if send_leaders:
            results['leaders_sent'], results['leaders_failed'] = send_leader_emails(
                offene_leiter_mails(only_unsent), connection=connection)
    finally:
        connection.close()
    return results
