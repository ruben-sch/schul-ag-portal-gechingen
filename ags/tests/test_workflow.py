import os
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from ags.models import AG, SchuelerProfile, Anmeldung, AppConfig, ArchivEintrag


class WorkflowTabTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create(username="admin@test.de", email="admin@test.de", is_staff=True)
        self.client.force_login(self.admin)
        self.ag = AG.objects.create(name="Fußball AG", kapazitaet=1, klassenstufe_min=1, klassenstufe_max=4,
                                    status='APPROVED', verantwortlicher_email='l@test.de', verantwortlicher_name='L')
        u = User.objects.create(username="eltern@test.de", email="eltern@test.de")
        self.profile = SchuelerProfile.objects.create(user=u, name="Kind", klassenstufe=2)
        Anmeldung.objects.create(schueler=self.profile, ag=self.ag, prio=1)

    def test_workflow_tab_is_default(self):
        res = self.client.get(reverse('stats_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Phase 1')
        self.assertContains(res, 'Phase 4')

    def test_toggle_flags(self):
        self.client.post(reverse('workflow_toggle'), {'name': 'anmeldung_offen', 'offen': '1'})
        self.assertTrue(AppConfig.load().anmeldung_offen)
        self.client.post(reverse('workflow_toggle'), {'name': 'ag_registrierung_offen', 'offen': '0'})
        self.assertFalse(AppConfig.load().ag_registrierung_offen)

    def test_toggle_rejects_unknown_field(self):
        self.client.post(reverse('workflow_toggle'), {'name': 'is_superuser', 'offen': '1'})
        self.assertFalse(AppConfig.load().anmeldung_offen)

    def test_toggle_requires_post_and_staff(self):
        self.assertEqual(self.client.get(reverse('workflow_toggle')).status_code, 405)
        self.client.logout()
        self.client.post(reverse('workflow_toggle'), {'name': 'anmeldung_offen', 'offen': '1'})
        self.assertFalse(AppConfig.load().anmeldung_offen)

    def test_lottery_runs_when_registration_closed(self):
        self.client.post(reverse('run_lottery_internal'))
        self.assertEqual(Anmeldung.objects.get().status, Anmeldung.Status.ACCEPTED)

    def test_lottery_requires_post(self):
        self.assertEqual(self.client.get(reverse('run_lottery_internal')).status_code, 405)

    def test_next_semester_requires_confirmation(self):
        self.client.post(reverse('workflow_next_semester'), {'bestaetigung': 'ja'})
        self.assertEqual(AG.objects.count(), 1)

    def test_next_semester_archives_and_resets(self):
        AppConfig.objects.update(ag_registrierung_offen=False)
        with tempfile.TemporaryDirectory() as backup_dir, override_settings(SEMESTER_BACKUP_DIR=backup_dir):
            self.client.post(reverse('workflow_next_semester'), {'bestaetigung': 'NEUES HALBJAHR'})
            self.assertEqual(len(os.listdir(backup_dir)), 1)
            # Zweiter Klick: nichts mehr zu archivieren, keine doppelten Archiveinträge.
            self.client.post(reverse('workflow_next_semester'), {'bestaetigung': 'NEUES HALBJAHR'})
        self.assertEqual(AG.objects.count(), 0)
        self.assertEqual(SchuelerProfile.objects.count(), 0)
        self.assertEqual(ArchivEintrag.objects.count(), 1)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())
        config = AppConfig.load()
        self.assertTrue(config.ag_registrierung_offen)
        self.assertFalse(config.anmeldung_offen)

    def test_lottery_blocked_after_final_mails(self):
        SchuelerProfile.objects.update(acceptance_email_sent=True)
        res = self.client.post(reverse('run_lottery_internal'), follow=True)
        self.assertContains(res, 'bereits verschickt')
        self.assertEqual(Anmeldung.objects.get().status, Anmeldung.Status.PENDING)

    def test_toggle_keeps_other_switch(self):
        from ags import services
        AppConfig.load()
        AppConfig.objects.update(anmeldung_offen=True)
        services.set_workflow_schalter('ag_registrierung_offen', False)
        config = AppConfig.load()
        self.assertTrue(config.anmeldung_offen)
        self.assertFalse(config.ag_registrierung_offen)

    def test_actions_return_to_their_tab(self):
        res = self.client.post(reverse('send_bulk_emails'), {'target': 'leaders', 'tab': 'general'})
        self.assertEqual(res.url, reverse('stats_dashboard') + '?tab=general')
        res = self.client.post(reverse('send_bulk_emails'), {'target': 'leaders'})
        self.assertEqual(res.url, reverse('stats_dashboard') + '?tab=workflow')
        res = self.client.post(reverse('send_bulk_emails'), {'target': 'leaders', 'tab': 'evil'})
        self.assertEqual(res.url, reverse('stats_dashboard') + '?tab=workflow')

    def test_reset_setzt_auslosung_zurueck(self):
        Anmeldung.objects.update(status=Anmeldung.Status.ACCEPTED)
        res = self.client.post(reverse('workflow_reset'), {'tab': 'workflow'})
        self.assertEqual(res.url, reverse('stats_dashboard') + '?tab=workflow')
        self.assertEqual(Anmeldung.objects.get().status, Anmeldung.Status.PENDING)

    def test_reset_nach_versand_zeigt_grund(self):
        Anmeldung.objects.update(status=Anmeldung.Status.ACCEPTED)
        SchuelerProfile.objects.update(acceptance_email_sent=True)
        res = self.client.post(reverse('workflow_reset'), follow=True)
        meldungen = [str(m) for m in res.context['messages']]
        self.assertTrue(any('bereits verschickt' in m for m in meldungen), meldungen)
        self.assertEqual(Anmeldung.objects.get().status, Anmeldung.Status.ACCEPTED)

    def test_workflow_tab_zeigt_reset_nur_nach_auslosung(self):
        res = self.client.get(reverse('stats_dashboard'))
        self.assertContains(res, 'disabled title="Noch nicht ausgelost."')
        Anmeldung.objects.update(status=Anmeldung.Status.ACCEPTED)
        res = self.client.get(reverse('stats_dashboard'))
        self.assertNotContains(res, 'disabled title="Noch nicht ausgelost."')
        self.assertContains(res, reverse('workflow_reset'))

    def test_vorschau_button_gesperrt_ohne_zusagen(self):
        Anmeldung.objects.update(status=Anmeldung.Status.REJECTED)
        res = self.client.get(reverse('stats_dashboard'))
        self.assertContains(res, 'disabled title="Vorläufige Listen gibt es erst nach der Auslosung."')

    def test_auslosen_button_im_allgemein_tab_zeigt_sperre(self):
        AppConfig.load()
        AppConfig.objects.update(anmeldung_offen=True)
        res = self.client.get(reverse('stats_dashboard') + '?tab=general')
        self.assertContains(res, 'disabled title="Die Anmeldung ist noch offen.')
