from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import AG, SchuelerProfile, Anmeldung, AppConfig, ArchivEintrag, TerminErinnerung

@admin.register(ArchivEintrag)
class ArchivEintragAdmin(admin.ModelAdmin):
    list_display = ('halbyahr', 'schueler_name', 'ag_name', 'status', 'datum')
    list_filter = ('halbyahr', 'status')
    search_fields = ('schueler_name', 'schueler_email', 'ag_name')
    readonly_fields = ('datum',)

    def has_add_permission(self, request):
        return False # Nur via System-Reset
from . import services

@admin.action(description='Ausgewählte AGs genehmigen')
def make_approved(modeladmin, request, queryset):
    queryset.update(status=AG.Status.APPROVED)

@admin.register(AG)
class AGAdmin(admin.ModelAdmin):
    list_display = ('name', 'verantwortlicher_name', 'get_termine_display', 'klassenstufe_min', 'klassenstufe_max', 'status', 'kapazitaet', 'leader_magic_link')
    list_filter = ('status', 'klassenstufe_min', 'klassenstufe_max')
    # Auslosen, Zurücksetzen und Versand laufen über den Workflow-Tab, damit dessen Sperren gelten.
    actions = [make_approved]
    search_fields = ('name', 'verantwortlicher_name', 'verantwortlicher_email')

    def leader_magic_link(self, obj):
        from sesame.utils import get_query_string
        from django.urls import reverse
        from django.utils.html import format_html
        
        # Get or create user for the leader so they can actually log in
        user = services.ensure_leader_user(obj)
        
        link = reverse('dashboard') + get_query_string(user)
        return format_html('<a href="{}" target="_blank">Leiter Login</a>', link)
    
    leader_magic_link.short_description = 'Leiter Magic Link'

from django.urls import reverse
from django.utils.html import format_html
from sesame.utils import get_query_string

@admin.register(SchuelerProfile)
class SchuelerProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'user_email', 'klassenstufe', 'magic_link_display')
    
    def user_email(self, obj):
        return obj.user.email

    def magic_link_display(self, obj):
        link = reverse('dashboard') + get_query_string(obj.user)
        return format_html('<a href="{}" target="_blank">Login Link</a>', link)
    
    magic_link_display.short_description = 'Magic Link'

@admin.register(Anmeldung)
class AnmeldungAdmin(admin.ModelAdmin):
    list_display = ('schueler', 'ag', 'prio', 'erstellt_am')
    list_filter = ('ag', 'prio')

@admin.register(AppConfig)
class AppConfigAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'anmeldung_offen')
    
    def has_add_permission(self, request):
        # Only one config allowed
        return not AppConfig.objects.exists()


@admin.register(TerminErinnerung)
class TerminErinnerungAdmin(admin.ModelAdmin):
    list_display = ('anmeldung', 'datum', 'gesendet_am', 'fehlgeschlagen')
    list_filter = ('datum', 'fehlgeschlagen')
    list_select_related = ('anmeldung__schueler', 'anmeldung__ag')
    readonly_fields = ('anmeldung', 'datum', 'gesendet_am', 'fehlgeschlagen')

    # Nur Protokoll: Einträge entstehen ausschließlich durch send_reminders.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
