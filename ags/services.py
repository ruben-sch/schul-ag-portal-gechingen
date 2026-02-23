from django.contrib.auth.models import User
from django.db.models import Count, Sum, Min, Max, Q
from .models import AG, SchuelerProfile, Anmeldung, AppConfig

def get_available_ags_for_student(klassenstufe):
    """Returns AGs suitable for a specific grade level."""
    return AG.objects.filter(
        status='APPROVED',
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
    available_ags = get_available_ags_for_student(student_profile.klassenstufe)
    available_ids = [str(ag.id) for ag in available_ags]
    
    valid_selections = [ag_id for ag_id in ag_ids if str(ag_id) in available_ids]
    
    Anmeldung.objects.filter(schueler=student_profile).delete()
    for i, ag_id in enumerate(valid_selections):
        ag = AG.objects.get(id=ag_id)
        Anmeldung.objects.create(schueler=student_profile, ag=ag, prio=i+1)
    
    return len(valid_selections) == len(ag_ids)

def get_student_dashboard_data(user):
    """Returns all registrations for student profiles linked to a user."""
    profiles = SchuelerProfile.objects.filter(user=user)
    return Anmeldung.objects.filter(schueler__in=profiles).select_related('ag', 'schueler')

def get_managed_ags_data(user):
    """Returns AGs managed by a user with prepared display data."""
    managed_ags = AG.objects.filter(verantwortlicher_email=user.email).prefetch_related(
        'anmeldungen__schueler'
    )
    
    for ag in managed_ags:
        ag.accepted_display = []
        ag.waiting_display = []
        anm_all = list(ag.anmeldungen.all())
        ag.total_count = len(anm_all)
        
        for reg in anm_all:
            profile = reg.schueler
            info_str = f"{profile.name} (Klasse {profile.klassenstufe}) - {profile.user.email} - Notfall: {profile.notfall_telefon}"
            
            if reg.status == 'ACCEPTED':
                ag.accepted_display.append(info_str)
            else:
                ag.waiting_display.append(f"{info_str} [Prio {reg.prio}]")
    
    return managed_ags

def get_portal_stats():
    """Returns global portal statistics."""
    total_schueler = SchuelerProfile.objects.count()
    total_anmeldungen = Anmeldung.objects.count()
    total_slots = AG.objects.filter(status='APPROVED').aggregate(Sum('kapazitaet'))['kapazitaet__sum'] or 0
    total_accepted = Anmeldung.objects.filter(status='ACCEPTED').count()
    
    profile_stats = SchuelerProfile.objects.annotate(
        accepted_count=Count('anmeldungen', filter=Q(anmeldungen__status='ACCEPTED'))
    ).aggregate(
        min_ags=Min('accepted_count'),
        max_ags=Max('accepted_count')
    )
    
    # Per AG stats
    ag_stats = AG.objects.filter(status='APPROVED').annotate(
        reg_count=Count('anmeldungen'),
        acc_count=Count('anmeldungen', filter=Q(anmeldungen__status='ACCEPTED'))
    ).prefetch_related('anmeldungen__schueler')
    
    for ag in ag_stats:
        ag.reg_percent = int(ag.reg_count * 100 / ag.kapazitaet) if ag.kapazitaet > 0 else 0
        ag.acc_percent = int(ag.acc_count * 100 / ag.kapazitaet) if ag.kapazitaet > 0 else 0
        ag.reg_percent_clamped = min(ag.reg_percent, 100)
        
        anm_list = list(ag.anmeldungen.all())
        ag.accepted_list = [a for a in anm_list if a.status == 'ACCEPTED']
        ag.waiting_list = [a for a in anm_list if a.status != 'ACCEPTED']
        ag.waiting_list.sort(key=lambda x: x.prio)
        
    return {
        'total_schueler': total_schueler,
        'total_anmeldungen': total_anmeldungen,
        'total_slots': total_slots,
        'total_accepted': total_accepted,
        'min_ags': profile_stats['min_ags'] or 0,
        'max_ags': profile_stats['max_ags'] or 0,
        'ag_stats': ag_stats
    }

def get_students_with_stats(search_query=None, min_ag_filter=None):
    """Returns students with their accepted AG count, optionally filtered."""
    students = SchuelerProfile.objects.annotate(
        accepted_count=Count('anmeldungen', filter=Q(anmeldungen__status='ACCEPTED'))
    ).prefetch_related('anmeldungen__ag').order_by('name')
    
    if search_query:
        students = students.filter(name__icontains=search_query)
    
    if min_ag_filter:
        try:
            students = students.filter(accepted_count__gte=int(min_ag_filter))
        except ValueError:
            pass
            
    return students
