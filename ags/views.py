import logging
from typing import Any
from smtplib import SMTPException
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, CreateView, FormView, UpdateView
from django.utils.decorators import method_decorator
from django.conf import settings
from datetime import datetime
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST
import csv
from django.db.models import Count, Sum, Min, Max, Q
from django.contrib.auth.decorators import login_required, user_passes_test
from sesame.utils import get_query_string
from .forms import AGProposalForm, AGEditForm, SchuelerFirstStepForm, LoginForm
from .models import AG, SchuelerProfile, Anmeldung, AppConfig, max_ag_wahlen
from .utils import run_lottery
from .emails import BCC_ADRESSE
from . import services

logger = logging.getLogger(__name__)

VERSAND_GESTARTET = ("Der E-Mail-Versand läuft im Hintergrund. "
                     "Lade die Seite in einigen Minuten neu, um den Gesendet-Status zu sehen.")

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
        services.ensure_leader_user(ag)
        messages.success(self.request, "Vielen Dank! Die AG wurde eingereicht und wird nun geprüft.")
        return super().form_valid(form)


@method_decorator(user_passes_test(lambda u: u.is_staff), name='dispatch')
class AGEditView(UpdateView):
    model = AG
    form_class = AGEditForm
    template_name = 'ags/propose_ag.html'
    success_url = reverse_lazy('stats_dashboard')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['edit_mode'] = True
        return context

    def get_success_url(self) -> str:
        return f"{self.success_url}?tab=ags"

    def form_valid(self, form: AGEditForm) -> HttpResponse:
        vorher = AG.objects.get(pk=self.object.pk).verantwortlicher_email
        leitung_geaendert = vorher.strip().lower() != form.cleaned_data['verantwortlicher_email']
        if leitung_geaendert:
            form.instance.leader_email_sent = False
        response = super().form_valid(form)
        services.ensure_leader_user(self.object)
        messages.success(self.request, f"AG \"{self.object.name}\" wurde gespeichert.")
        if leitung_geaendert:
            messages.info(self.request, "Die AG-Leitung wurde geändert. Die Teilnehmerliste muss erneut verschickt werden.")
        for warnung in services.ag_bearbeiten_warnungen(self.object):
            messages.warning(self.request, warnung)
        return response

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

def select_ags(request: HttpRequest) -> HttpResponse:
    reg_data = request.session.get('reg_data')
    if not reg_data:
        return redirect('register_schueler')
    
    klasse = reg_data['klassenstufe']
    available_ags = services.get_available_ags_for_student(klasse)
    
    if request.method == 'POST':
        selected_ag_ids = request.POST.getlist('ags')
        
        if not selected_ag_ids:
            messages.error(request, "Bitte wähle mindestens eine gültige AG aus.")
        elif len(selected_ag_ids) > max_ag_wahlen():
            messages.error(request, f"Es dürfen maximal {max_ag_wahlen()} AGs ausgewählt werden.")
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
        'reg_data': reg_data,
        'max_ag_wahlen': max_ag_wahlen(),
    })

class RequestMagicLinkView(FormView):
    form_class = LoginForm
    template_name = 'ags/login.html'
    success_url = reverse_lazy('landing')

    def form_valid(self, form):
        email = form.cleaned_data['email']
        user = User.objects.filter(email__iexact=email).order_by('id').first()
        if user is not None:
            link = self.request.build_absolute_uri(reverse('dashboard'))
            link += get_query_string(user)
            print(f"MAGIC LINK FOR {email}: {link}")
            messages.success(self.request, f"Ein Anmelde-Link wurde an {email} gesendet (siehe Server-Log).")
            return super().form_valid(form)
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

@require_POST
@user_passes_test(lambda u: u.is_staff)
def duplicate_ag(request: HttpRequest, pk: int) -> HttpResponse:
    kopie = services.duplicate_ag(get_object_or_404(AG, pk=pk))
    messages.success(request, f"AG \"{kopie.name}\" wurde kopiert. Bitte jetzt die neuen Termine eintragen.")
    return redirect('edit_ag', pk=kopie.pk)


@user_passes_test(lambda u: u.is_staff)
def stats_dashboard(request: HttpRequest) -> HttpResponse:
    tab = request.GET.get('tab', 'workflow')
    stats = services.get_portal_stats() if tab in ['general', 'ags'] else {}
    if tab == 'workflow':
        stats = services.get_workflow_status()
    
    # Per Student stats if needed
    search_query = request.GET.get('student_search', '')
    min_ag_filter = request.GET.get('min_ags', '')
    sort_by = request.GET.get('sort_by', 'name')
    
    students = services.get_students_with_stats(search_query, min_ag_filter, sort_by) if tab == 'students' else []

    return render(request, 'ags/stats.html', {
        **stats,
        'students': students,
        'search_query': search_query,
        'min_ag_filter': min_ag_filter,
        'sort_by': sort_by,
        'tab': tab
    })

DASHBOARD_TABS = ('workflow', 'general', 'ags', 'students')


def _zurueck_zum_dashboard(request: HttpRequest) -> HttpResponse:
    """Leitet nach einer Aktion in den Dashboard-Tab zurück, aus dem das Formular kam."""
    tab = request.POST.get('tab')
    if tab not in DASHBOARD_TABS:
        tab = 'workflow'
    return redirect(f"{reverse('stats_dashboard')}?tab={tab}")


@require_POST
@user_passes_test(lambda u: u.is_staff)
def run_lottery_view(request: HttpRequest) -> HttpResponse:
    blocked = services.lottery_blocked_reason()
    if blocked:
        messages.error(request, blocked)
    else:
        run_lottery()
        messages.success(request, "Das Losverfahren wurde erfolgreich durchgeführt.")
    return _zurueck_zum_dashboard(request)


@require_POST
@user_passes_test(lambda u: u.is_staff)
def workflow_toggle(request: HttpRequest) -> HttpResponse:
    name = request.POST.get('name')
    offen = request.POST.get('offen') == '1'
    try:
        services.set_workflow_schalter(name, offen)
    except ValueError:
        messages.error(request, "Unbekannte Einstellung.")
    else:
        label = 'AG-Registrierung' if name == 'ag_registrierung_offen' else 'Anmeldung'
        messages.success(request, f"{label} ist jetzt {'geöffnet' if offen else 'geschlossen'}.")
    return _zurueck_zum_dashboard(request)


@require_POST
@user_passes_test(lambda u: u.is_staff)
def workflow_next_semester(request: HttpRequest) -> HttpResponse:
    if request.POST.get('bestaetigung') != 'NEUES HALBJAHR':
        messages.error(request, "Bitte zur Bestätigung NEUES HALBJAHR eingeben.")
        return _zurueck_zum_dashboard(request)
    services.start_new_semester()
    messages.success(request, "Das Halbjahr wurde archiviert und das System für die neue Runde zurückgesetzt.")
    return _zurueck_zum_dashboard(request)

@user_passes_test(lambda u: u.is_staff)
def manual_intervention(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        action = request.POST.get('action')
        anm_id = request.POST.get('anmeldung_id')
        
        try:
            if action == 'send_all_unsent':
                from .tasks import send_allocation_emails_task
                send_allocation_emails_task.enqueue(only_unsent=True)
                messages.success(request, VERSAND_GESTARTET)
            else:
                anm = Anmeldung.objects.get(id=anm_id)
                if action == 'toggle_status':
                    anm.status = Anmeldung.Status.REJECTED if anm.status == Anmeldung.Status.ACCEPTED else Anmeldung.Status.ACCEPTED
                    anm.save()
                    messages.success(request, f"Status für {anm.schueler.name} in {anm.ag.name} geändert.")
                elif action == 'update_prio':
                    new_prio = request.POST.get('prio')
                    if new_prio and new_prio.isdigit():
                        prio_val = int(new_prio)
                        if 1 <= prio_val <= max_ag_wahlen():
                            anm.prio = prio_val
                            anm.save()
                            messages.success(request, f"Priorität für {anm.schueler.name} in {anm.ag.name} auf {new_prio} aktualisiert.")
                        else:
                            messages.error(request, f"Priorität muss zwischen 1 und {max_ag_wahlen()} liegen.")
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
        'search_query': search_query,
        'max_ag_wahlen': max_ag_wahlen(),
    })

@user_passes_test(lambda u: u.is_staff)
def resend_email(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        email_type = request.POST.get('email_type')
        
        try:
            profile = SchuelerProfile.objects.get(id=student_id)
            if email_type == 'confirmation':
                if profile.anmeldungen.exists():
                    from .tasks import send_registration_confirmation_task
                    send_registration_confirmation_task.enqueue(profile.id)
                    messages.success(request, f"Anmeldebestätigung an {profile.user.email} wird versendet.")
                else:
                    messages.warning(request, "Schüler hat keine Anmeldungen.")
            elif email_type == 'acceptance':
                from .tasks import send_acceptance_email_task
                send_acceptance_email_task.enqueue(profile.id)
                messages.success(request, f"Zuteilungsmail an {profile.user.email} wird versendet.")
        except SchuelerProfile.DoesNotExist:
            messages.error(request, "Schüler nicht gefunden.")
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim E-Mail-Nachversand: {e}", exc_info=True)
            messages.error(request, "Ein Fehler ist aufgetreten.")
            
    return redirect('manual_intervention')

@user_passes_test(lambda u: u.is_staff)
def resend_leader_email(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        ag_id = request.POST.get('ag_id')
        try:
            ag = AG.objects.get(id=ag_id)
            if request.POST.get('kind') == 'preview':
                sperrgrund = services.leader_preview_blocked_reason(ag)
                if sperrgrund:
                    messages.error(request, sperrgrund)
                else:
                    from .tasks import send_leader_preview_email_task
                    send_leader_preview_email_task.enqueue(ag.id)
                    messages.success(request, f"Vorläufige Liste für AG-Leitung ({ag.verantwortlicher_email}) wird versendet.")
            else:
                from .tasks import send_leader_email_task
                send_leader_email_task.enqueue(ag.id)
                messages.success(request, f"E-Mail für AG-Leitung ({ag.verantwortlicher_email}) wird versendet.")
        except AG.DoesNotExist:
            messages.error(request, "AG nicht gefunden.")
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim AG-Leiter E-Mail-Nachversand: {e}", exc_info=True)
            messages.error(request, "Ein Fehler ist aufgetreten.")
            
    return _zurueck_zum_dashboard(request)

@user_passes_test(lambda u: u.is_staff)
def stats_export(request):
    # This view is optimized for printing
    stats = services.get_portal_stats()
    
    return render(request, 'ags/stats_export.html', {
        **stats,
        'date': datetime.now()
    })

@user_passes_test(lambda u: u.is_staff)
def test_email(request: HttpRequest) -> HttpResponse:
    try:
        user_email = request.user.email
        if not user_email:
            messages.error(request, "Dein Benutzerkonto hat keine E-Mail-Adresse hinterlegt.")
            return redirect('stats_dashboard')
            
        msg = EmailMultiAlternatives(
            subject='Geplante Test-E-Mail (AG-Portal)',
            body=f'Hallo {request.user.first_name},\n\ndies ist eine Test-E-Mail aus dem AG-Portal. Wenn diese Nachricht ankommt, ist der E-Mail-Versand korrekt konfiguriert.\n\nViele Grüße,\nDein AG-Portal System',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email],
            bcc=[BCC_ADRESSE]
        )
        msg.send(fail_silently=False)
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

@user_passes_test(lambda u: u.is_staff)
def send_bulk_emails_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        target = request.POST.get('target')
        from .tasks import send_allocation_emails_task

        if target == 'students':
            send_allocation_emails_task.enqueue(only_unsent=True, send_students=True, send_leaders=False)
            messages.success(request, VERSAND_GESTARTET)
        elif target == 'leaders':
            send_allocation_emails_task.enqueue(only_unsent=True, send_students=False, send_leaders=True)
            messages.success(request, VERSAND_GESTARTET)
        elif target == 'leader_preview':
            sperrgrund = services.leader_preview_blocked_reason()
            if sperrgrund:
                messages.error(request, sperrgrund)
            else:
                from .tasks import send_leader_preview_emails_task
                send_leader_preview_emails_task.enqueue(only_unsent=True)
                messages.success(request, VERSAND_GESTARTET)
        else:
            messages.error(request, "Ungültiges Zielfeld für den E-Mail-Versand.")

    return _zurueck_zum_dashboard(request)
