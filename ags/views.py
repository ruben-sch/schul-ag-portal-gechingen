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
from .models import AG, SchuelerProfile, Anmeldung, AppConfig
from .forms import AGProposalForm, SchuelerFirstStepForm, LoginForm
from .utils import run_lottery
from . import services


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
    available_ags = services.get_available_ags_for_student(klasse)
    
    if request.method == 'POST':
        selected_ag_ids = request.POST.getlist('ags')
        
        if not selected_ag_ids:
            messages.error(request, "Bitte wähle mindestens eine gültige AG aus.")
        else:
            # Create/Get user and profile
            email = reg_data['email']
            user, _ = User.objects.get_or_create(username=email, defaults={'email': email})
            
            profile = services.register_or_update_student(
                user, reg_data['name'], klasse, reg_data.get('notfall_telefon', '')
            )
            
            # Save selections
            all_valid = services.update_student_registrations(profile, selected_ag_ids)
            
            if not all_valid:
                messages.warning(request, "Einige gewählte AGs waren nicht für deine Klassenstufe zugelassen und wurden ignoriert.")

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
    anmeldungen = services.get_student_dashboard_data(request.user)
    managed_ags = services.get_managed_ags_data(request.user)
    is_parent = SchuelerProfile.objects.filter(user=request.user).exists()
    
    return render(request, 'ags/dashboard.html', {
        'anmeldungen': anmeldungen,
        'managed_ags': managed_ags,
        'is_parent': is_parent
    })

@user_passes_test(lambda u: u.is_staff)
def stats_dashboard(request):
    stats = services.get_portal_stats()
    
    # Per Student stats
    search_query = request.GET.get('student_search', '')
    min_ag_filter = request.GET.get('min_ags', '')
    
    students = services.get_students_with_stats(search_query, min_ag_filter)

    return render(request, 'ags/stats.html', {
        **stats,
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
    stats = services.get_portal_stats()
    
    return render(request, 'ags/stats_export.html', {
        **stats,
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

def impressum(request):
    return render(request, 'ags/impressum.html')
