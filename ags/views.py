import logging
from smtplib import SMTPException
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, CreateView, FormView
from django.conf import settings
from datetime import datetime
from django.http import HttpResponse
import csv
from django.db.models import Count, Sum, Min, Max, Q
from django.contrib.auth.decorators import login_required, user_passes_test
from sesame.utils import get_query_string
from .forms import AGProposalForm, SchuelerFirstStepForm, LoginForm
from .models import AG, SchuelerProfile, Anmeldung, AppConfig
from .utils import run_lottery
from . import services

logger = logging.getLogger(__name__)

class LandingView(TemplateView):
    template_name = 'ags/landing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = AppConfig.load()
        context['anmeldung_offen'] = config.anmeldung_offen if config else False
        context['ag_registrierung_offen'] = config.ag_registrierung_offen if config else True
        return context

class ProposeAGView(CreateView):
    model = AG
    form_class = AGProposalForm
    template_name = 'ags/propose_ag.html'
    success_url = reverse_lazy('landing')

    def dispatch(self, request, *args, **kwargs):
        config = AppConfig.load()
        if config and not config.ag_registrierung_offen:
            messages.error(request, "Das Einreichen neuer AGs ist zur Zeit deaktiviert.")
            return redirect('landing')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        ag = form.save()
        User.objects.get_or_create(
            username=ag.verantwortlicher_email,
            defaults={
                'email': ag.verantwortlicher_email,
                'first_name': ag.verantwortlicher_name
            }
        )
        messages.success(self.request, "Vielen Dank! Die AG wurde eingereicht und wird nun geprüft.")
        return super().form_valid(form)

class RegisterSchuelerStep1View(FormView):
    form_class = SchuelerFirstStepForm
    template_name = 'ags/register_step1.html'
    success_url = reverse_lazy('select_ags')

    def dispatch(self, request, *args, **kwargs):
        config = AppConfig.load()
        if config and not config.anmeldung_offen:
            messages.error(request, "Die Anmeldephase ist zur Zeit geschlossen.")
            return redirect('landing')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.request.session['reg_data'] = form.cleaned_data
        return super().form_valid(form)

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

class RequestMagicLinkView(FormView):
    form_class = LoginForm
    template_name = 'ags/login.html'
    success_url = reverse_lazy('landing')

    def form_valid(self, form):
        email = form.cleaned_data['email']
        try:
            user = User.objects.get(email=email)
            link = self.request.build_absolute_uri(reverse('dashboard'))
            link += get_query_string(user)
            print(f"MAGIC LINK FOR {email}: {link}")
            messages.success(self.request, f"Ein Anmelde-Link wurde an {email} gesendet (siehe Server-Log).")
            return super().form_valid(form)
        except User.DoesNotExist:
            messages.error(self.request, "Diese E-Mail-Adresse ist nicht bekannt.")
            return self.form_invalid(form)

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
            if action == 'send_all_unsent':
                from .emails import send_allocation_emails
                send_allocation_emails(only_unsent=True)
                messages.success(request, "Alle fehlenden Zuteilungs-Mails wurden (sofern möglich) erfolgreich versendet.")
            else:
                anm = Anmeldung.objects.get(id=anm_id)
                if action == 'toggle_status':
                    anm.status = Anmeldung.Status.REJECTED if anm.status == Anmeldung.Status.ACCEPTED else Anmeldung.Status.ACCEPTED
                    anm.save()
                    messages.success(request, f"Status für {anm.schueler.name} in {anm.ag.name} geändert.")
                elif action == 'update_prio':
                    new_prio = request.POST.get('prio')
                    if new_prio and new_prio.isdigit():
                        anm.prio = int(new_prio)
                        anm.save()
                        messages.success(request, f"Priorität für {anm.schueler.name} in {anm.ag.name} auf {new_prio} aktualisiert.")
        except Anmeldung.DoesNotExist:
            logger.warning(f"Anmeldung mit ID {anm_id} nicht gefunden in manual_intervention.")
            messages.error(request, "Ausgewählte Anmeldung konnte nicht gefunden werden.")
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei manual_intervention (ID: {anm_id}): {e}", exc_info=True)
            messages.error(request, "Ein unerwarteter Fehler ist aufgetreten.")
            
        # Preserve search query on POST redirect if it exists
        search_query = request.GET.get('search_query', '')
        url = reverse('manual_intervention')
        if search_query:
            url += f"?search_query={search_query}"
        return redirect(url)

    # Data for display
    search_query = request.GET.get('search_query', '')
    ags = AG.objects.filter(status=AG.Status.APPROVED).prefetch_related('anmeldungen__schueler')
    
    students = SchuelerProfile.objects.prefetch_related('anmeldungen__ag').order_by('name')
    if search_query:
        students = students.filter(name__icontains=search_query)
        
    return render(request, 'ags/manual_intervention.html', {
        'ags': ags,
        'students': students,
        'search_query': search_query
    })

@user_passes_test(lambda u: u.is_staff)
def resend_email(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        email_type = request.POST.get('email_type')
        
        try:
            profile = SchuelerProfile.objects.get(id=student_id)
            if email_type == 'confirmation':
                from django.template.loader import render_to_string
                from django.utils.html import strip_tags
                anmeldungen = list(Anmeldung.objects.filter(schueler=profile).order_by('prio'))
                if anmeldungen:
                    context = {'schueler': profile, 'anmeldungen': anmeldungen}
                    html_message = render_to_string('ags/emails/registration_confirmation.html', context)
                    plain_message = strip_tags(html_message)
                    send_mail(
                        "Deine Schul-AG Anmeldung",
                        plain_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [profile.user.email],
                        html_message=html_message,
                    )
                    profile.confirmation_email_sent = True
                    profile.save()
                    messages.success(request, f"Anmeldebestätigung an {profile.user.email} gesendet.")
                else:
                    messages.warning(request, f"Schüler hat keine Anmeldungen.")
            elif email_type == 'acceptance':
                from .emails import send_single_acceptance_email
                success = send_single_acceptance_email(profile)
                if success:
                    messages.success(request, f"Zuteilungsmail an {profile.user.email} gesendet.")
                else:
                    messages.error(request, f"Fehler beim Senden der Zuteilungsmail an {profile.user.email}.")
        except SchuelerProfile.DoesNotExist:
            messages.error(request, "Schüler nicht gefunden.")
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim E-Mail-Nachversand: {e}", exc_info=True)
            messages.error(request, "Ein Fehler ist aufgetreten.")
            
    return redirect('manual_intervention')

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
    except SMTPException as e:
        logger.error(f"SMTP Fehler beim E-Mail-Versand an {user_email}: {e}", exc_info=True)
        messages.error(request, "SMTP Fehler beim E-Mail-Versand. Bitte Server-Logs prüfen.")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim E-Mail-Versand an {user_email}: {e}", exc_info=True)
        messages.error(request, "Ein unerwarteter Fehler ist aufgetreten. Bitte Server-Logs prüfen.")
        
    return redirect('stats_dashboard')

def impressum(request):
    return render(request, 'ags/impressum.html')

@user_passes_test(lambda u: u.is_staff)
def export_ags_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="ags_flyer_export.csv"'
    
    writer = csv.writer(response, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
    
    writer.writerow([
        "titel", "klassen", "datum", "start", "ende", "leitung", 
        "ort", "kosten", "maxkinder", "mitbringen", "beschreibung", 
        "orga_info", "bild"
    ])
    
    ags = AG.objects.filter(status='APPROVED').order_by('name')
    for ag in ags:
        # Format classes
        klassen = [f"{k}. Klasse" for k in range(ag.klassenstufe_min, ag.klassenstufe_max + 1)]
        klassen_str = ", ".join(klassen)
        
        # Format dates (from JSON)
        termine_dates = []
        termine_starts = []
        termine_endes = []
        
        if isinstance(ag.termine, list):
            for t in ag.termine:
                d = t.get('datum', '')
                if '-' in d and len(d) == 10:
                    y, m, day = d.split('-')
                    d = f"{day}.{m}.{y}"
                if d:
                    termine_dates.append(d)
                if t.get('start'):
                    termine_starts.append(t.get('start'))
                if t.get('ende'):
                    termine_endes.append(t.get('ende'))
                
        datum_str = " / ".join(filter(None, termine_dates))
        if len(termine_starts) > 0 and len(set(termine_starts)) == 1:
            start_str = termine_starts[0]
            ende_str = termine_endes[0] if len(termine_endes) > 0 else ""
        else:
            start_str = " / ".join(filter(None, termine_starts))
            ende_str = " / ".join(filter(None, termine_endes))
            
        leitung_str = f"{ag.verantwortlicher_name} {ag.verantwortlicher_telefon}".strip()
        kosten_str = f"{ag.kosten}€" if ag.kosten else "0€"
        
        writer.writerow([
            ag.name,
            klassen_str,
            datum_str,
            start_str,
            ende_str,
            leitung_str,
            ag.ort or '',
            kosten_str,
            str(ag.kapazitaet),
            ag.mitzubringen or '',
            ag.beschreibung or '',
            ag.hinweise or '',
            "images/placeholder.png"
        ])
        
    return response

