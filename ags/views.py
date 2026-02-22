from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from datetime import datetime
from django.db.models import Count, Sum, Min, Max, Q
from django.contrib.auth.decorators import login_required, user_passes_test
from sesame.utils import get_query_string
from .forms import AGProposalForm, SchuelerFirstStepForm, LoginForm
from .models import AG, SchuelerProfile, Anmeldung, AppConfig
from .utils import run_lottery


def landing(request):
    config = AppConfig.objects.first()
    return render(request, 'ags/landing.html', {
        'anmeldung_offen': config.anmeldung_offen if config else False,
        'ag_registrierung_offen': config.ag_registrierung_offen if config else True
    })

def propose_ag(request):
    config = AppConfig.objects.first()
    if config and not config.ag_registrierung_offen:
        messages.error(request, "Das Einreichen neuer AGs ist zur Zeit deaktiviert.")
        return redirect('landing')

    if request.method == 'POST':
        form = AGProposalForm(request.POST)
        if form.is_valid():
            ag = form.save()
            
            # Ensure leader has a User account for dashboard access
            User.objects.get_or_create(
                username=ag.verantwortlicher_email,
                defaults={
                    'email': ag.verantwortlicher_email,
                    'first_name': ag.verantwortlicher_name
                }
            )
            
            messages.success(request, "Vielen Dank! Die AG wurde eingereicht und wird nun geprüft.")
            return redirect('landing')
    else:
        form = AGProposalForm()
    return render(request, 'ags/propose_ag.html', {'form': form})

def register_schueler(request):
    config = AppConfig.objects.first()
    if config and not config.anmeldung_offen:
        messages.error(request, "Die Anmeldephase ist zur Zeit geschlossen.")
        return redirect('landing')

    if request.method == 'POST':
        form = SchuelerFirstStepForm(request.POST)
        if form.is_valid():
            # Save data in session for step 2
            request.session['reg_data'] = form.cleaned_data
            return redirect('select_ags')
    else:
        form = SchuelerFirstStepForm()
    return render(request, 'ags/register_step1.html', {'form': form})

def select_ags(request):
    reg_data = request.session.get('reg_data')
    if not reg_data:
        return redirect('register_schueler')
    
    klasse = reg_data['klassenstufe']
    available_ags = AG.objects.filter(
        status='APPROVED',
        klassenstufe_min__lte=klasse,
        klassenstufe_max__gte=klasse
    )
    
    if request.method == 'POST':
        selected_ag_ids = request.POST.getlist('ags')
        
        # Validation: Ensure all selected AGs are actually valid for this student's grade
        available_ids = [str(ag.id) for ag in available_ags]
        valid_selections = [ag_id for ag_id in selected_ag_ids if ag_id in available_ids]
        
        if not valid_selections:
            messages.error(request, "Bitte wähle mindestens eine gültige AG aus.")
        else:
            if len(valid_selections) != len(selected_ag_ids):
                messages.warning(request, "Einige gewählte AGs waren nicht für deine Klassenstufe zugelassen und wurden ignoriert.")

            # Create user if not exists or get existing
            email = reg_data['email']
            user, created = User.objects.get_or_create(
                username=email,
                defaults={'email': email}
            )
            
            # Identify student by name AND user (email) to allow siblings
            student_name = reg_data['name']
            profile, _ = SchuelerProfile.objects.get_or_create(
                user=user,
                name=student_name,
                defaults={
                    'klassenstufe': klasse,
                    'notfall_telefon': reg_data.get('notfall_telefon', '')
                }
            )
            # Ensure details are updated
            profile.klassenstufe = klasse
            profile.notfall_telefon = reg_data.get('notfall_telefon', '')
            profile.save()
            
            # Save selections for this specific profile
            Anmeldung.objects.filter(schueler=profile).delete()
            for i, ag_id in enumerate(valid_selections):
                ag = AG.objects.get(id=ag_id)
                Anmeldung.objects.create(schueler=profile, ag=ag, prio=i+1)
            
            del request.session['reg_data']
            messages.success(request, "Anmeldung erfolgreich gespeichert!")
            return redirect('landing')
            
    return render(request, 'ags/register_step2.html', {
        'ags': available_ags,
        'reg_data': reg_data
    })

def request_magic_link(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                # Generate Magic Link
                link = request.build_absolute_uri(reverse('dashboard'))
                link += get_query_string(user)
                
                # In a real app, send email here. For now, print to console/show message.
                print(f"MAGIC LINK FOR {email}: {link}")
                messages.success(request, f"Ein Anmelde-Link wurde an {email} gesendet (siehe Server-Log).")
                return redirect('landing')
            except User.DoesNotExist:
                messages.error(request, "Diese E-Mail-Adresse ist nicht bekannt.")
    else:
        form = LoginForm()
    return render(request, 'ags/login.html', {'form': form})

@login_required
def dashboard(request):
    # Determine if user is schueler and/or leiter
    # For students: Get all registrations for all profiles linked to this user
    profiles = SchuelerProfile.objects.filter(user=request.user)
    anmeldungen = Anmeldung.objects.filter(schueler__in=profiles).select_related('ag', 'schueler')
    
    # Check if user is a verantwortlicher for any AGs
    managed_ags = AG.objects.filter(verantwortlicher_email=request.user.email).prefetch_related(
        'anmeldungen__schueler'
    )
    
    # Prepare data in python to avoid template tag issues
    for ag in managed_ags:
        ag.accepted_display = []
        ag.waiting_display = []
        anm_all = list(ag.anmeldungen.all())
        ag.total_count = len(anm_all)
        
        for reg in anm_all:
            profile = reg.schueler
            klasse = profile.klassenstufe
            phone = profile.notfall_telefon
            email = profile.user.email
            name = profile.name
            
            info_str = f"{name} (Klasse {klasse}) - {email} - Notfall: {phone}"
            
            if reg.status == 'ACCEPTED':
                ag.accepted_display.append(info_str)
            else:
                ag.waiting_display.append(f"{info_str} [Prio {reg.prio}]")
    
    return render(request, 'ags/dashboard.html', {
        'anmeldungen': anmeldungen,
        'managed_ags': managed_ags,
        'is_parent': profiles.exists()
    })

@user_passes_test(lambda u: u.is_staff)
def stats_dashboard(request):
    total_schueler = SchuelerProfile.objects.count()
    total_anmeldungen = Anmeldung.objects.count()
    total_slots = AG.objects.filter(status='APPROVED').aggregate(Sum('kapazitaet'))['kapazitaet__sum'] or 0
    total_accepted = Anmeldung.objects.filter(status='ACCEPTED').count()
    
    # Calculate min/max accepted AGs per student profile
    profile_stats = SchuelerProfile.objects.annotate(
        accepted_count=Count('anmeldungen', filter=Q(anmeldungen__status='ACCEPTED'))
    ).aggregate(
        min_ags=Min('accepted_count'),
        max_ags=Max('accepted_count')
    )
    
    # Per AG stats with lists
    ag_stats = AG.objects.filter(status='APPROVED').annotate(
        reg_count=Count('anmeldungen'),
        acc_count=Count('anmeldungen', filter=Q(anmeldungen__status='ACCEPTED'))
    ).prefetch_related('anmeldungen__schueler')
    
    # Per Student stats
    search_query = request.GET.get('student_search', '')
    min_ag_filter = request.GET.get('min_ags', '')
    
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

    # Calculate percentages and prepare display lists
    for ag in ag_stats:
        ag.reg_percent = int(ag.reg_count * 100 / ag.kapazitaet) if ag.kapazitaet > 0 else 0
        ag.acc_percent = int(ag.acc_count * 100 / ag.kapazitaet) if ag.kapazitaet > 0 else 0
        ag.reg_percent_clamped = min(ag.reg_percent, 100)
        
        # Sort and prepare participants
        anm_list = list(ag.anmeldungen.all())
        ag.accepted_list = [a for a in anm_list if a.status == 'ACCEPTED']
        ag.waiting_list = [a for a in anm_list if a.status != 'ACCEPTED']
        ag.waiting_list.sort(key=lambda x: x.prio)

    return render(request, 'ags/stats.html', {
        'total_schueler': total_schueler,
        'total_anmeldungen': total_anmeldungen,
        'total_slots': total_slots,
        'total_accepted': total_accepted,
        'min_ags': profile_stats['min_ags'] or 0,
        'max_ags': profile_stats['max_ags'] or 0,
        'ag_stats': ag_stats,
        'students': students,
        'search_query': search_query,
        'min_ag_filter': min_ag_filter
    })

@user_passes_test(lambda u: u.is_staff)
def run_lottery_view(request):
    run_lottery()
    messages.success(request, "Das Losverfahren wurde erfolgreich durchgeführt.")
    return redirect('stats_dashboard')

@user_passes_test(lambda u: u.is_staff)
def manual_intervention(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        anm_id = request.POST.get('anmeldung_id')
        
        try:
            anm = Anmeldung.objects.get(id=anm_id)
            if action == 'toggle_status':
                anm.status = 'REJECTED' if anm.status == 'ACCEPTED' else 'ACCEPTED'
                anm.save()
                messages.success(request, f"Status für {anm.schueler.name} in {anm.ag.name} geändert.")
        except Exception as e:
            messages.error(request, f"Fehler: {str(e)}")
        
        return redirect('manual_intervention')

    # Data for display
    ags = AG.objects.filter(status='APPROVED').prefetch_related('anmeldungen__schueler')
    students = SchuelerProfile.objects.prefetch_related('anmeldungen__ag').order_by('name')
    
    return render(request, 'ags/manual_intervention.html', {
        'ags': ags,
        'students': students
    })

@user_passes_test(lambda u: u.is_staff)
def stats_export(request):
    # This view is optimized for printing
    ag_stats = AG.objects.filter(status='APPROVED').annotate(
        reg_count=Count('anmeldungen'),
        acc_count=Count('anmeldungen', filter=Q(anmeldungen__status='ACCEPTED'))
    ).prefetch_related('anmeldungen__schueler')
    
    total_schueler = SchuelerProfile.objects.count()
    
    return render(request, 'ags/stats_export.html', {
        'ag_stats': ag_stats,
        'total_schueler': total_schueler,
        'date': datetime.now()
    })

@user_passes_test(lambda u: u.is_staff)
def test_email(request):
    try:
        user_email = request.user.email
        if not user_email:
            messages.error(request, "Dein Benutzerkonto hat keine E-Mail-Adresse hinterlegt.")
            return redirect('stats_dashboard')
            
        send_mail(
            subject='Geplante Test-E-Mail (AG-Portal)',
            message=f'Hallo {request.user.first_name},\n\ndies ist eine Test-E-Mail aus dem AG-Portal. Wenn diese Nachricht ankommt, ist der E-Mail-Versand korrekt konfiguriert.\n\nViele Grüße,\nDein AG-Portal System',
            from_email=None,  # Uses DEFAULT_FROM_EMAIL
            recipient_list=[user_email],
            fail_silently=False,
        )
        messages.success(request, f"Test-E-Mail wurde erfolgreich an {user_email} (oder an die Konsole) versendet.")
    except Exception as e:
        messages.error(request, f"Fehler beim E-Mail-Versand: {str(e)}")
        
    return redirect('stats_dashboard')
