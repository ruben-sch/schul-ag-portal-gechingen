"""
Hintergrund-Aufgaben (Django Tasks). In Produktion arbeitet sie der Worker-Container
(`python manage.py db_worker`) ab, damit lange E-Mail-Läufe keine Web-Requests blockieren.
"""
from django.tasks import task

from . import emails
from .models import AG, SchuelerProfile


@task
def send_allocation_emails_task(only_unsent=True, send_students=True, send_leaders=True):
    return emails.send_allocation_emails(only_unsent=only_unsent, send_students=send_students, send_leaders=send_leaders)


@task
def send_acceptance_email_task(schueler_id):
    schueler = SchuelerProfile.objects.select_related('user').get(id=schueler_id)
    return emails.send_single_acceptance_email(schueler)


@task
def send_leader_email_task(ag_id):
    return emails.send_single_leader_email(AG.objects.get(id=ag_id))


@task
def send_registration_confirmation_task(schueler_id):
    schueler = SchuelerProfile.objects.select_related('user').get(id=schueler_id)
    return emails.send_registration_confirmation(schueler)
