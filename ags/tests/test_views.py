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

    def test_csv_export_flyer(self):
        user = User.objects.create(username="admin_csv@test.de", is_staff=True)
        self.client.force_login(user)
        
        self.ag1.beschreibung = "Wir töpfern dieses Mal kleine Tannenbäume und Nikoläuse.  Ihr solltet beide Termine einplanen, da wir beim ersten Termin modellieren und eure gebrannten Werke zwei Wochen später glasieren."
        self.ag1.kosten = 5
        self.ag1.mitzubringen = "Kleidung die dreckig werden darf"
        self.ag1.hinweise = "Bitte auch hier noch einen zweiten Termin hinzufügen: 7.11.25. 15:00-16:00"
        self.ag1.ort = "Werkraum"
        self.ag1.termine = [{"datum": "2025-10-24", "start": "15:00", "ende": "16:30"}, {"datum": "2025-11-07", "start": "15:00", "ende": "16:30"}]
        self.ag1.save()
        
        # Test expects this endpoint to exist and return strictly formatted CSV
        res = self.client.get(reverse('export_ags_csv'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'text/csv; charset=utf-8')
        
        content = res.content.decode('utf-8')
        lines = content.strip().split('\n')
        self.assertTrue(len(lines) > 1)
        
        header = '"titel","klassen","datum","start","ende","leitung","ort","kosten","maxkinder","mitbringen","beschreibung","orga_info","bild"'
        self.assertEqual(lines[0].strip('\r'), header)
        
        # We check some substrings in the first valid data row
        row = lines[1]
        self.assertIn('Roboter AG', row)
        self.assertIn('1. Klasse, 2. Klasse', row)  # Must format classes properly!
        self.assertIn('images/placeholder.png', row)  # Placeholder constraint
