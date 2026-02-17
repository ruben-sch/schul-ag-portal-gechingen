from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import AG, SchuelerProfile, Anmeldung, AppConfig
from .utils import run_lottery, reset_lottery
import sesame.utils

class AGPortalTest(TestCase):
    def setUp(self):
        # Setup AppConfig
        AppConfig.objects.create(anmeldung_offen=True)
        
        # Setup AGs
        self.ag1 = AG.objects.create(
            name="Roboter AG",
            beschreibung="Robots",
            kapazitaet=1,
            klassenstufe_min=1,
            klassenstufe_max=4,
            status='APPROVED',
            verantwortlicher_email='leiter@test.de',
            verantwortlicher_name='Herr Leiter'
        )
        self.ag2 = AG.objects.create(
            name="Sport AG",
            beschreibung="Sport",
            kapazitaet=10,
            klassenstufe_min=1,
            klassenstufe_max=2,
            status='APPROVED',
            verantwortlicher_email='leiter2@test.de',
            verantwortlicher_name='Frau Sport'
        )

    def test_sibling_registration(self):
        client = Client()
        email = "familie@test.de"
        
        # Register Child 1
        res1 = client.post(reverse('register_schueler'), {
            'name': 'Max Kind',
            'email': email,
            'klassenstufe': 4,
            'notfall_telefon': '110'
        })
        self.assertEqual(res1.status_code, 302) # Redirect to select_ags
        client.post(reverse('select_ags'), {'ags': [self.ag1.id]})
        
        # Register Child 2 (Sibling)
        res2 = client.post(reverse('register_schueler'), {
            'name': 'Moritz Kind',
            'email': email,
            'klassenstufe': 2,
            'notfall_telefon': '112'
        })
        self.assertEqual(res2.status_code, 302) # Redirect to select_ags
        client.post(reverse('select_ags'), {'ags': [self.ag2.id]})
        
        # Verify DB structure
        user = User.objects.get(email=email)
        profiles = SchuelerProfile.objects.filter(user=user)
        self.assertEqual(profiles.count(), 2)
        
        max_profile = profiles.get(name='Max Kind')
        self.assertEqual(max_profile.klassenstufe, 4)
        
        moritz_profile = profiles.get(name='Moritz Kind')
        self.assertEqual(moritz_profile.klassenstufe, 2)
        
        # Check Anmeldungen
        self.assertEqual(Anmeldung.objects.filter(schueler=max_profile).count(), 1)
        self.assertEqual(Anmeldung.objects.filter(schueler=moritz_profile).count(), 1)

    def test_lottery_utilization_and_fairness(self):
        # Add another student competing for the same slot
        user2 = User.objects.create(username="other@test.de", email="other@test.de")
        other_profile = SchuelerProfile.objects.create(
            user=user2, name="Other Student", klassenstufe=4, notfall_telefon="999"
        )
        
        # Both want ag1 (capacity 1)
        user1 = User.objects.create(username="sibling@test.de", email="sibling@test.de")
        sibling_profile = SchuelerProfile.objects.create(
            user=user1, name="Sibling", klassenstufe=4, notfall_telefon="111"
        )
        
        Anmeldung.objects.create(schueler=other_profile, ag=self.ag1, prio=1)
        Anmeldung.objects.create(schueler=sibling_profile, ag=self.ag1, prio=1)
        
        run_lottery()
        
        # Total accepted should be matching capacity
        self.assertEqual(Anmeldung.objects.filter(ag=self.ag1, status='ACCEPTED').count(), 1)
        self.assertEqual(Anmeldung.objects.filter(status='ACCEPTED').count(), 1)
        
        # Test reset
        reset_lottery()
        self.assertEqual(Anmeldung.objects.filter(status='ACCEPTED').count(), 0)
        self.assertEqual(Anmeldung.objects.filter(status='PENDING').count(), 2)

    def test_dashboard_access_and_layout(self):
        # Create a parent with 2 kids
        user = User.objects.create(username="parent@test.de", email="parent@test.de")
        k1 = SchuelerProfile.objects.create(user=user, name="Kid 1", klassenstufe=1)
        k2 = SchuelerProfile.objects.create(user=user, name="Kid 2", klassenstufe=2)
        
        Anmeldung.objects.create(schueler=k1, ag=self.ag2, status='ACCEPTED')
        Anmeldung.objects.create(schueler=k2, ag=self.ag2, status='REJECTED')
        
        client = Client()
        client.force_login(user)
        
        res = client.get(reverse('dashboard'))
        self.assertContains(res, "Kid 1")
        self.assertContains(res, "Kid 2")
        self.assertContains(res, "Sport AG")
        self.assertContains(res, "Zugelassen")
        self.assertContains(res, "Warteliste")

    def test_leader_dashboard_info_vertical(self):
        # Create a student with full info
        user = User.objects.create(username="kid@test.de", email="kid@test.de")
        profile = SchuelerProfile.objects.create(user=user, name="Kid FullInfo", klassenstufe=1, notfall_telefon="555-NOTFALL")
        
        Anmeldung.objects.create(schueler=profile, ag=self.ag1, status='ACCEPTED', prio=1)
        
        # Create leader user
        leader_user = User.objects.create(username="leiter@test.de", email="leiter@test.de")
        
        client = Client()
        client.force_login(leader_user)
        
        res = client.get(reverse('dashboard'))
        self.assertContains(res, "Deine AG-Verwaltung")
        self.assertContains(res, "Kid FullInfo")
        self.assertContains(res, "Klasse 1")
        self.assertContains(res, "kid@test.de")
        self.assertContains(res, "Notfall: 555-NOTFALL")
        
    def test_grade_level_validation(self):
        user = User.objects.create(username="wrong@test.de", email="wrong@test.de")
        profile = SchuelerProfile.objects.create(user=user, name="Wrong Grade", klassenstufe=4)
        
        # AG2 is for grades 1-2. Student is grade 4.
        with self.assertRaises(Exception): # models.clean() raises ValidationError which results in Exception here if save() is overridden
            Anmeldung.objects.create(schueler=profile, ag=self.ag2)
