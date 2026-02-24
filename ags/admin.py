from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import AG, SchuelerProfile, Anmeldung, AppConfig, ArchivEintrag

@admin.register(ArchivEintrag)
class ArchivEintragAdmin(admin.ModelAdmin):
    list_display = ('halbyahr', 'schueler_name', 'ag_name', 'status', 'datum')
    list_filter = ('halbyahr', 'status')
    search_fields = ('schueler_name', 'schueler_email', 'ag_name')
    readonly_fields = ('datum',)

    def has_add_permission(self, request):
        return False # Nur via System-Reset
from .utils import run_lottery, reset_lottery
from .emails import send_allocation_emails

@admin.action(description='Ausgewählte AGs genehmigen')
def make_approved(modeladmin, request, queryset):
    queryset.update(status='APPROVED')

@admin.action(description='Losverfahren starten')
def trigger_lottery(modeladmin, request, queryset):
    run_lottery()
    modeladmin.message_user(request, "Losverfahren wurde ausgeführt.")

@admin.action(description='Zuteilungen zurücksetzen (Undo)')
def undo_lottery(modeladmin, request, queryset):
    reset_lottery()
    modeladmin.message_user(request, "Zuteilungen wurden zurückgesetzt.")

from django.core.management import call_command

@admin.action(description='System für neues Halbjahr zurücksetzen (Archiviert alte Daten)')
def start_next_semester(modeladmin, request, queryset):
    call_command('next_semester')
    modeladmin.message_user(request, "Das System wurde archiviert und für das neue Halbjahr zurückgesetzt.")

@admin.action(description='Ergebnisse per E-Mail versenden')
def trigger_emails(modeladmin, request, queryset):
    send_allocation_emails()
    modeladmin.message_user(request, "Benachrichtigungen wurden versendet.")

@admin.register(AG)
class AGAdmin(admin.ModelAdmin):
    list_display = ('name', 'verantwortlicher_name', 'get_termine_display', 'klassenstufe_min', 'klassenstufe_max', 'status', 'kapazitaet', 'leader_magic_link')
    list_filter = ('status', 'klassenstufe_min', 'klassenstufe_max')
    actions = [make_approved, trigger_lottery, undo_lottery, trigger_emails]
    search_fields = ('name', 'verantwortlicher_name', 'verantwortlicher_email')

    def leader_magic_link(self, obj):
        from django.contrib.auth.models import User
        from sesame.utils import get_query_string
        from django.urls import reverse
        from django.utils.html import format_html
        
        # Get or create user for the leader so they can actually log in
        user, created = User.objects.get_or_create(
            username=obj.verantwortlicher_email,
            defaults={'email': obj.verantwortlicher_email, 'first_name': obj.verantwortlicher_name}
        )
        
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
    actions = [start_next_semester]
    
    def has_add_permission(self, request):
        # Only one config allowed
        return not AppConfig.objects.exists()
