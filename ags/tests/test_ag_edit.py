from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from ags import services
from ags.models import AG, Anmeldung, SchuelerProfile


class AGEditTest(TestCase):
    def setUp(self):
        self.ag = AG.objects.create(name="Kunst AG", beschreibung="Malen", kapazitaet=10, klassenstufe_min=1, klassenstufe_max=4,
                                    termine=[{'datum': '2026-11-03', 'start': '14:00', 'ende': '15:00'}],
                                    verantwortlicher_email='kunst@test.de', verantwortlicher_name='Herr Pinsel')
        self.url = reverse('edit_ag', args=[self.ag.pk])
        self.staff = User.objects.create(username="staff@test.de", is_staff=True)

    def _data(self, **overrides):
        data = {
            'name': 'Kunst AG', 'beschreibung': 'Malen', 'kosten': 5, 'klassenstufe_min': 1, 'klassenstufe_max': 4,
            'kapazitaet': 12, 'ort': 'Werkraum', 'termine': '[{"datum": "2026-11-10", "start": "13:00", "ende": "14:30"}]',
            'mitzubringen': '', 'hinweise': '', 'verantwortlicher_name': 'Herr Pinsel',
            'verantwortlicher_email': 'neu@test.de', 'verantwortlicher_telefon': '', 'status': 'APPROVED',
        }
        data.update(overrides)
        return data

    def test_requires_staff(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 302)
        self.client.force_login(User.objects.create(username="eltern@test.de"))
        res = self.client.post(self.url, self._data())
        self.assertEqual(res.status_code, 302)
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.kapazitaet, 10)

    def test_edit_form_prefilled(self):
        self.client.force_login(self.staff)
        res = self.client.get(self.url)
        self.assertContains(res, 'AG bearbeiten')
        self.assertContains(res, '2026-11-03')
        self.assertContains(res, 'name="status"')

    def test_save_changes_including_termine_and_status(self):
        self.client.force_login(self.staff)
        res = self.client.post(self.url, self._data())
        self.assertRedirects(res, reverse('stats_dashboard') + '?tab=ags', fetch_redirect_response=False)
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.kapazitaet, 12)
        self.assertEqual(self.ag.ort, 'Werkraum')
        self.assertEqual(self.ag.termine, [{'datum': '2026-11-10', 'start': '13:00', 'ende': '14:30'}])
        self.assertEqual(self.ag.status, AG.Status.APPROVED)
        self.assertTrue(User.objects.filter(username='neu@test.de').exists())

    def test_pending_ags_listed_with_edit_link(self):
        self.client.force_login(self.staff)
        res = self.client.get(reverse('stats_dashboard') + '?tab=ags')
        self.assertContains(res, 'noch nicht genehmigt')
        self.assertContains(res, self.url)

    def _anmeldung(self, klassenstufe=2, status=Anmeldung.Status.ACCEPTED, name="Kind"):
        eltern = User.objects.create(username=f"{name}@eltern.de", email=f"{name}@eltern.de")
        profil = SchuelerProfile.objects.create(user=eltern, name=name, klassenstufe=klassenstufe)
        return Anmeldung.objects.create(schueler=profil, ag=self.ag, prio=1, status=status)

    def test_invalid_grade_range_rerenders_without_saving(self):
        self.client.force_login(self.staff)
        res = self.client.post(self.url, self._data(klassenstufe_min=4, klassenstufe_max=2))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context['edit_mode'])
        self.assertContains(res, 'nicht kleiner als die niedrigste')
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.kapazitaet, 10)
        self.assertEqual(self.ag.verantwortlicher_email, 'kunst@test.de')

    def test_model_save_rejects_inverted_grade_range(self):
        from django.core.exceptions import ValidationError
        self.ag.klassenstufe_min, self.ag.klassenstufe_max = 3, 2
        with self.assertRaises(ValidationError):
            self.ag.save()

    def test_leader_change_reuses_existing_user_and_resets_mail_flag(self):
        User.objects.create(username='altkonto', email='Neu@Test.de')
        AG.objects.filter(pk=self.ag.pk).update(leader_email_sent=True)
        self.client.force_login(self.staff)
        res = self.client.post(self.url, self._data(verantwortlicher_email=' NEU@test.de '), follow=True)
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.verantwortlicher_email, 'neu@test.de')
        self.assertFalse(self.ag.leader_email_sent)
        self.assertEqual(User.objects.filter(email__iexact='neu@test.de').count(), 1)
        self.assertContains(res, 'AG-Leitung wurde geändert')

    def test_unchanged_leader_keeps_mail_flag(self):
        AG.objects.filter(pk=self.ag.pk).update(leader_email_sent=True)
        self.client.force_login(self.staff)
        self.client.post(self.url, self._data(verantwortlicher_email='KUNST@test.de'))
        self.ag.refresh_from_db()
        self.assertTrue(self.ag.leader_email_sent)

    def test_cannot_unapprove_ag_with_registrations(self):
        AG.objects.filter(pk=self.ag.pk).update(status=AG.Status.APPROVED)
        self._anmeldung(status=Anmeldung.Status.PENDING)
        self.client.force_login(self.staff)
        res = self.client.post(self.url, self._data(status='SUBMITTED'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'bereits Anmeldungen')
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.status, AG.Status.APPROVED)

    def test_warns_on_capacity_and_grade_conflicts(self):
        AG.objects.filter(pk=self.ag.pk).update(status=AG.Status.APPROVED)
        self._anmeldung(klassenstufe=1, name="Anna")
        self._anmeldung(klassenstufe=3, name="Ben")
        self.client.force_login(self.staff)
        res = self.client.post(self.url, self._data(kapazitaet=1, klassenstufe_min=2), follow=True)
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.kapazitaet, 1)
        self.assertContains(res, 'bereits 2 Kinder zugelassen')
        self.assertContains(res, '1 Anmeldung(en) liegen außerhalb')

    def test_login_finds_leader_case_insensitively(self):
        self.client.force_login(self.staff)
        self.client.post(self.url, self._data(verantwortlicher_email='Leitung@Test.de'))
        self.client.logout()
        res = self.client.post(reverse('login'), {'email': 'LEITUNG@test.de'}, follow=True)
        self.assertContains(res, 'Anmelde-Link wurde')


class AGDuplicateTest(TestCase):
    def setUp(self):
        # Jedes Inhaltsfeld bekommt einen Nicht-Standardwert, damit ein vergessenes Feld auffällt.
        self.ag = AG.objects.create(name="Kunst AG", beschreibung="Malen", kosten=5, kapazitaet=10, klassenstufe_min=2,
                                    klassenstufe_max=3, ort='Werkraum', mitzubringen='Malkittel', hinweise='Bitte pünktlich',
                                    status='APPROVED', leader_email_sent=True,
                                    termine=[{'datum': '2026-11-03', 'start': '14:00', 'ende': '15:00'}],
                                    verantwortlicher_email='kunst@test.de', verantwortlicher_name='Herr Pinsel',
                                    verantwortlicher_telefon='07056 1234')
        u = User.objects.create(username="eltern@test.de", email="eltern@test.de")
        p = SchuelerProfile.objects.create(user=u, name="Kind", klassenstufe=2)
        Anmeldung.objects.create(schueler=p, ag=self.ag, prio=1)
        self.url = reverse('duplicate_ag', args=[self.ag.pk])

    def test_duplicate_copies_content_without_termine_and_registrations(self):
        self.client.force_login(User.objects.create(username="staff@test.de", is_staff=True))
        res = self.client.post(self.url)
        kopie = AG.objects.exclude(pk=self.ag.pk).get()
        self.assertRedirects(res, reverse('edit_ag', args=[kopie.pk]), fetch_redirect_response=False)
        for feld in services.AG_INHALT_FELDER:
            self.assertEqual(getattr(kopie, feld), getattr(self.ag, feld), feld)
            self.assertNotEqual(getattr(self.ag, feld), AG._meta.get_field(feld).get_default(), feld)
        self.assertEqual(kopie.termine, [])
        self.assertEqual(kopie.status, AG.Status.SUBMITTED)
        self.assertFalse(kopie.leader_email_sent)
        self.assertEqual(kopie.anmeldungen.count(), 0)

    def test_duplicate_requires_post_and_staff(self):
        self.client.force_login(User.objects.create(username="staff@test.de", is_staff=True))
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.force_login(User.objects.create(username="eltern2@test.de"))
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('login'), res.url)
        self.assertEqual(AG.objects.count(), 1)

    def test_duplicate_rejects_anonymous(self):
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(AG.objects.count(), 1)
