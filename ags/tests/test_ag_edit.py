from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from ags.models import AG


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
        self.client.post(self.url, self._data())
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
