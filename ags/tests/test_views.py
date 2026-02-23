from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ags.models import AG, SchuelerProfile, Anmeldung, AppConfig
from ags import services

class ViewTest(TestCase):
    def setUp(self):
        self.config = AppConfig.load()
        self.config.anmeldung_offen = True
        self.config.save()
        
        self.ag1 = AG.objects.create(
            name="Roboter AG",
            kapazitaet=1,
            klassenstufe_min=1,
            klassenstufe_max=4,
            status='APPROVED',
            verantwortlicher_email='leiter@test.de',
            verantwortlicher_name='Herr Leiter'
        )
        self.client = Client()

    def test_landing_page(self):
        res = self.client.get(reverse('landing'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Willkommen")

    def test_registration_flow(self):
        # Step 1
        res = self.client.post(reverse('register_schueler'), {
            'name': 'Max Kind',
            'email': 'familie@test.de',
            'klassenstufe': 4,
            'notfall_telefon': '110'
        })
        self.assertEqual(res.status_code, 302)
        
        # Step 2
        res = self.client.post(reverse('select_ags'), {'ags': [self.ag1.id]})
        self.assertEqual(res.status_code, 302)
        
        # Verify
        user = User.objects.get(email='familie@test.de')
        profile = SchuelerProfile.objects.get(user=user, name='Max Kind')
        self.assertEqual(Anmeldung.objects.filter(schueler=profile).count(), 1)

    def test_dashboard_access(self):
        user = User.objects.create(username="test@test.de", email="test@test.de")
        self.client.force_login(user)
        res = self.client.get(reverse('dashboard'))
        self.assertEqual(res.status_code, 200)

    def test_staff_access_required(self):
        user = User.objects.create(username="user@test.de")
        self.client.force_login(user)
        res = self.client.get(reverse('stats_dashboard'))
        self.assertEqual(res.status_code, 302) # Redirect to login
        
        user.is_staff = True
        user.save()
        res = self.client.get(reverse('stats_dashboard'))
        self.assertEqual(res.status_code, 200)
