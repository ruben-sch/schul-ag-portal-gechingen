import logging

from django.contrib.auth.models import User
from django.db.models import Count, Sum, Min, Max, Q
from .models import AG, SchuelerProfile, Anmeldung, AppConfig, max_ag_wahlen

logger = logging.getLogger(__name__)

def get_available_ags_for_student(klassenstufe):
    """Returns AGs suitable for a specific grade level."""
    return AG.objects.filter(
        status=AG.Status.APPROVED,
        klassenstufe_min__lte=klassenstufe,
        klassenstufe_max__gte=klassenstufe
    )

def register_or_update_student(user, name, klassenstufe, notfall_telefon):
    """Creates or updates a student profile and ensures the User exists."""
    profile, created = SchuelerProfile.objects.get_or_create(
        user=user,
        name=name,
        defaults={
            'klassenstufe': klassenstufe,
            'notfall_telefon': notfall_telefon
        }
    )
    if not created:
        profile.klassenstufe = klassenstufe
        profile.notfall_telefon = notfall_telefon
        profile.save()
    return profile

def update_student_registrations(student_profile, ag_ids):
    """Replaces current registrations for a student with new selections."""
    from django.db import transaction

    available_ags = get_available_ags_for_student(student_profile.klassenstufe)
    available_ids = [str(ag.id) for ag in available_ags]
    
    valid_selections = [ag_id for ag_id in ag_ids if str(ag_id) in available_ids][:max_ag_wahlen()]
    
    with transaction.atomic():
        Anmeldung.objects.filter(schueler=student_profile).delete()
        for i, ag_id in enumerate(valid_selections):
            ag = AG.objects.get(id=ag_id)
            Anmeldung.objects.create(schueler=student_profile, ag=ag, prio=i+1)
        student_profile.confirmation_email_sent = False
        student_profile.acceptance_email_sent = False
        student_profile.save(update_fields=['confirmation_email_sent', 'acceptance_email_sent'])
        # Erst nach dem Commit einreihen, damit der Worker die gespeicherte Anmeldung sieht.
        transaction.on_commit(lambda: _bestaetigung_einreihen(student_profile.id))

    return len(valid_selections) == len(ag_ids)


def _bestaetigung_einreihen(schueler_id):
    """
    Reiht die Anmeldebestätigung im Hintergrund ein. Scheitert das Einreihen, bleibt die Anmeldung
    gültig; confirmation_email_sent bleibt False, sodass der Admin die Bestätigung nachsenden kann.
    """
    from .tasks import send_registration_confirmation_task
    try:
        send_registration_confirmation_task.enqueue(schueler_id)
    except Exception:
        logger.exception("Anmeldebestätigung für Schüler %s konnte nicht eingereiht werden.", schueler_id)

def get_student_dashboard_data(user):
    """Returns all registrations for student profiles linked to a user."""
    profiles = SchuelerProfile.objects.filter(user=user)
    return Anmeldung.objects.filter(schueler__in=profiles).select_related('ag', 'schueler')

def get_managed_ags_data(user):
    """Returns AGs managed by a user with prepared display data."""
    managed_ags = AG.objects.filter(verantwortlicher_email__iexact=user.email).prefetch_related(
        'anmeldungen__schueler'
    )
    
    for ag in managed_ags:
        ag.accepted_list = []
        ag.waiting_list = []
        anm_all = list(ag.anmeldungen.all())
        ag.total_count = len(anm_all)
        
        for reg in anm_all:
            if reg.status == Anmeldung.Status.ACCEPTED:
                ag.accepted_list.append(reg)
            else:
                ag.waiting_list.append(reg)
    
    return managed_ags

def get_portal_stats():
    """Returns global portal statistics."""
    total_schueler = SchuelerProfile.objects.count()
    total_anmeldungen = Anmeldung.objects.count()
    total_slots = AG.objects.filter(status=AG.Status.APPROVED).aggregate(Sum('kapazitaet'))['kapazitaet__sum'] or 0
    total_accepted = Anmeldung.objects.filter(status=Anmeldung.Status.ACCEPTED).count()
    
    profile_stats = SchuelerProfile.objects.annotate(
        accepted_count=Count('anmeldungen', filter=Q(anmeldungen__status=Anmeldung.Status.ACCEPTED))
    ).aggregate(
        min_ags=Min('accepted_count'),
        max_ags=Max('accepted_count')
    )
    
    # Per AG stats
    ag_stats = AG.objects.filter(status=AG.Status.APPROVED).annotate(
        reg_count=Count('anmeldungen'),
        acc_count=Count('anmeldungen', filter=Q(anmeldungen__status=Anmeldung.Status.ACCEPTED))
    ).prefetch_related('anmeldungen__schueler')
    
    for ag in ag_stats:
        ag.reg_percent = int(ag.reg_count * 100 / ag.kapazitaet) if ag.kapazitaet > 0 else 0
        ag.acc_percent = int(ag.acc_count * 100 / ag.kapazitaet) if ag.kapazitaet > 0 else 0
        ag.reg_percent_clamped = min(ag.reg_percent, 100)
        
        anm_list = list(ag.anmeldungen.all())
        ag.accepted_list = [a for a in anm_list if a.status == Anmeldung.Status.ACCEPTED]
        ag.waiting_list = [a for a in anm_list if a.status != Anmeldung.Status.ACCEPTED]
        ag.waiting_list.sort(key=lambda x: x.prio)
        
    return {
        'total_schueler': total_schueler,
        'total_anmeldungen': total_anmeldungen,
        'total_slots': total_slots,
        'total_accepted': total_accepted,
        'min_ags': profile_stats['min_ags'] or 0,
        'max_ags': profile_stats['max_ags'] or 0,
        'ag_stats': ag_stats,
        'pending_ags': AG.objects.exclude(status=AG.Status.APPROVED).order_by('name'),
    }

def get_students_with_stats(search_query=None, min_ag_filter=None, sort_by='name'):
    """Returns students with their accepted AG count, optionally filtered and sorted."""
    students = SchuelerProfile.objects.annotate(
        accepted_count=Count('anmeldungen', filter=Q(anmeldungen__status=Anmeldung.Status.ACCEPTED))
    ).prefetch_related('anmeldungen__ag')
    
    if search_query:
        students = students.filter(name__icontains=search_query)
    
    if min_ag_filter:
        try:
            students = students.filter(accepted_count__gte=int(min_ag_filter))
        except ValueError:
            pass
            
    if sort_by in ['name', '-name']:
        students = students.order_by(sort_by)
    elif sort_by in ['accepted_count', '-accepted_count']:
        students = students.order_by(sort_by, 'name')
    else:
        students = students.order_by('name')
            
    return students


def leader_preview_blocked_reason(ag=None):
    """Grund, warum keine vorläufige Liste verschickt werden darf, sonst None."""
    if (Anmeldung.objects.filter(status=Anmeldung.Status.PENDING).exists()
            or not Anmeldung.objects.filter(status=Anmeldung.Status.ACCEPTED).exists()):
        return "Vorläufige Listen gibt es erst nach der Auslosung."
    if ag is not None and ag.leader_email_sent:
        return f"Für {ag.name} wurde die endgültige Liste bereits verschickt."
    return None


WORKFLOW_SCHALTER = ('ag_registrierung_offen', 'anmeldung_offen')


def get_workflow_status():
    """Kennzahlen für den Workflow-Tab im Admin-Bereich (Phasen 1-4 eines Halbjahres)."""
    config = AppConfig.load()
    approved = AG.objects.filter(status=AG.Status.APPROVED)
    zugeteilte = SchuelerProfile.objects.filter(anmeldungen__status=Anmeldung.Status.ACCEPTED).distinct()
    return {
        'config': config,
        'ag_count': AG.objects.count(),
        'ag_approved_count': approved.count(),
        'schueler_count': SchuelerProfile.objects.count(),
        'anmeldung_count': Anmeldung.objects.count(),
        'lottery_done': Anmeldung.objects.exclude(status=Anmeldung.Status.PENDING).exists(),
        'preview_sent_count': approved.filter(leader_preview_sent=True).count(),
        'leader_sent_count': approved.filter(leader_email_sent=True).count(),
        'zugeteilte_count': zugeteilte.count(),
        'acceptance_sent_count': zugeteilte.filter(acceptance_email_sent=True).count(),
        'lottery_blocked': lottery_blocked_reason(),
    }


def set_workflow_schalter(name, offen):
    """Schaltet AG-Registrierung oder Schüler-Anmeldung an/aus."""
    if name not in WORKFLOW_SCHALTER:
        raise ValueError(f"Unbekannter Schalter: {name}")
    config = AppConfig.load()
    # Nur das eine Feld schreiben, sonst überschreibt ein gleichzeitiges Schalten den anderen Schalter.
    AppConfig.objects.filter(pk=config.pk).update(**{name: offen})
    config.refresh_from_db()
    return config


def lottery_blocked_reason():
    """Gibt einen Grund zurück, warum die Auslosung gerade nicht laufen darf, sonst None."""
    if AppConfig.load().anmeldung_offen:
        return "Die Anmeldung ist noch offen. Bitte zuerst die Anmeldung schließen, dann auslosen."
    # Eine neue Zuteilung würde nie verschickt (nur ungesendete Mails gehen raus), Eltern behielten die alte.
    if (AG.objects.filter(leader_email_sent=True).exists()
            or SchuelerProfile.objects.filter(acceptance_email_sent=True).exists()):
        return ("Die endgültigen Mails wurden bereits verschickt. Eine neue Auslosung würde die verschickten "
                "Zuteilungen ungültig machen; Änderungen bitte über die manuelle Korrektur.")
    return None


def start_new_semester():
    """
    Archiviert das Halbjahr und setzt das System zurück (wie `make next-semester`), in einer Transaktion:
    Bricht der Request ab, bleibt kein halb gelöschter Zustand. Die Sperre auf AppConfig serialisiert
    Doppelklicks; der zweite Lauf findet dann nichts mehr zum Archivieren. Die Ausgabe des Commands
    (inkl. JSON-Dump mit personenbezogenen Daten) landet bewusst nicht im Log.
    """
    import io
    from django.core.management import call_command
    from django.db import transaction

    AppConfig.load()
    with transaction.atomic():
        AppConfig.objects.select_for_update().get(pk=1)
        call_command('next_semester', stdout=io.StringIO())


def ensure_leader_user(ag):
    """Legt für die AG-Leitung ein Benutzerkonto an, damit sie sich per Magic Link anmelden kann.

    Ein vorhandenes Konto mit derselben E-Mail (Groß-/Kleinschreibung egal) wird wiederverwendet,
    damit Login und Leiter-Dashboard eindeutig bleiben.
    """
    email = ag.verantwortlicher_email.strip().lower()
    user = (User.objects.filter(email__iexact=email).order_by('id').first()
            or User.objects.filter(username__iexact=email).order_by('id').first())
    if user is None:
        return User.objects.create(username=email, email=email, first_name=ag.verantwortlicher_name)
    if not user.email or not user.first_name:
        user.email = user.email or email
        user.first_name = user.first_name or ag.verantwortlicher_name
        user.save(update_fields=['email', 'first_name'])
    return user


def ag_bearbeiten_warnungen(ag):
    """Hinweise, wenn eine geänderte AG nicht mehr zu den vorhandenen Anmeldungen passt."""
    warnungen = []
    zugelassen = ag.anmeldungen.filter(status=Anmeldung.Status.ACCEPTED).count()
    if zugelassen > ag.kapazitaet:
        warnungen.append(
            f"Es sind bereits {zugelassen} Kinder zugelassen, die Kapazität beträgt jetzt aber nur {ag.kapazitaet}."
        )
    ausserhalb = ag.anmeldungen.exclude(
        schueler__klassenstufe__range=(ag.klassenstufe_min, ag.klassenstufe_max)
    ).count()
    if ausserhalb:
        warnungen.append(
            f"{ausserhalb} Anmeldung(en) liegen außerhalb der neuen Klassenstufen "
            f"{ag.klassenstufe_min}–{ag.klassenstufe_max}."
        )
    return warnungen


# Inhaltliche Felder einer AG; Status, Versand-Flags und Anmeldungen gehören nicht dazu.
AG_INHALT_FELDER = (
    'name', 'beschreibung', 'kosten', 'klassenstufe_min', 'klassenstufe_max', 'kapazitaet', 'ort',
    'mitzubringen', 'hinweise', 'verantwortlicher_name', 'verantwortlicher_email', 'verantwortlicher_telefon',
)


def duplicate_ag(ag):
    """Kopiert eine AG ohne Termine und Anmeldungen, damit sie zu einem anderen Termin erneut angeboten werden kann."""
    return AG.objects.create(
        **{feld: getattr(ag, feld) for feld in AG_INHALT_FELDER},
        termine=[],
        status=AG.Status.SUBMITTED,
    )
