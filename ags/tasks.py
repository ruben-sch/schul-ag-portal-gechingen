"""
Hintergrund-Aufgaben (Django Tasks). In Produktion arbeitet sie der Worker-Container
(`python manage.py db_worker`) ab, damit lange E-Mail-Läufe keine Web-Requests blockieren.

Fehlgeschlagene Mails lassen den Task mit EmailVersandFehler scheitern, damit sie im Admin
unter „Tasks Database Backend“ als FAILED sichtbar sind und nicht nur im Log stehen.
"""
from django.tasks import task

from . import emails
from .models import AG, SchuelerProfile

# Bulk-Versand in kleinen Paketen: Bestätigungen kommen zwischen zwei Paketen dran, und ein
# Neustart des Workers (Deploy) unterbricht höchstens ein Paket statt des ganzen Laufs.
PAKETGROESSE = 10
# Höher als der Standard (0), damit Anmeldebestätigungen vor wartenden Bulk-Paketen laufen.
PRIORITAET_BESTAETIGUNG = 10


class EmailVersandFehler(Exception):
    pass


def _pakete(ids):
    return [ids[i:i + PAKETGROESSE] for i in range(0, len(ids), PAKETGROESSE)]


def _pruefen(art, sent, failed):
    if failed:
        raise EmailVersandFehler(f"{failed} von {sent + failed} {art} konnten nicht gesendet werden (Details im Log).")
    return {'sent': sent, 'failed': failed}


@task
def send_allocation_emails_task(only_unsent=True, send_students=True, send_leaders=True):
    """Verteilt den Bulk-Versand auf Paket-Tasks und gibt die Zahl der Pakete zurück."""
    pakete = 0
    if send_students:
        for paket in _pakete(emails.offene_zusagen(only_unsent)):
            send_acceptance_batch_task.enqueue(paket, only_unsent=only_unsent)
            pakete += 1
    if send_leaders:
        for paket in _pakete(emails.offene_leiter_mails(only_unsent)):
            send_leader_batch_task.enqueue(paket, only_unsent=only_unsent)
            pakete += 1
    return pakete


@task
def send_acceptance_batch_task(schueler_ids, only_unsent=True):
    # only_unsent wird hier erneut geprüft, damit ein doppelt gestarteter Versand keine Mail zweimal schickt.
    return _pruefen("Zuteilungsmails", *emails.send_acceptance_emails(schueler_ids, only_unsent=only_unsent))


@task
def send_leader_batch_task(ag_ids, only_unsent=True):
    return _pruefen("Leiter-Mails", *emails.send_leader_emails(ag_ids, only_unsent=only_unsent))


@task
def send_acceptance_email_task(schueler_id):
    schueler = SchuelerProfile.objects.select_related('user').get(id=schueler_id)
    if not emails.send_single_acceptance_email(schueler):
        raise EmailVersandFehler(f"Zuteilungsmail an {schueler.user.email} konnte nicht gesendet werden.")


@task
def send_leader_email_task(ag_id):
    ag = AG.objects.get(id=ag_id)
    if emails.send_single_leader_email(ag) is False:
        raise EmailVersandFehler(f"Leiter-Mail für {ag.name} konnte nicht gesendet werden.")


@task(priority=PRIORITAET_BESTAETIGUNG)
def send_registration_confirmation_task(schueler_id):
    schueler = SchuelerProfile.objects.select_related('user').get(id=schueler_id)
    if not emails.send_registration_confirmation(schueler):
        raise EmailVersandFehler(f"Anmeldebestätigung an {schueler.user.email} konnte nicht gesendet werden.")
