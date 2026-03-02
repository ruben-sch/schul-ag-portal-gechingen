from django.test import TestCase
from django.contrib.auth.models import User
from ags.models import AG, SchuelerProfile, Anmeldung, AppConfig
from ags.utils import run_lottery, reset_lottery

class LotteryTest(TestCase):
    def setUp(self):
        AppConfig.load().save()
        self.ag1 = AG.objects.create(
            name="Beliebte AG", kapazitaet=1, 
            klassenstufe_min=1, klassenstufe_max=4, status='APPROVED'
        )
        
    def test_lottery_utilization_and_fairness(self):
        # 2 students for 1 slot
        u1 = User.objects.create(username="u1@test.de", email="u1@test.de")
        p1 = SchuelerProfile.objects.create(user=u1, name="S1", klassenstufe=1)
        Anmeldung.objects.create(schueler=p1, ag=self.ag1, prio=1)
        
        u2 = User.objects.create(username="u2@test.de", email="u2@test.de")
        p2 = SchuelerProfile.objects.create(user=u2, name="S2", klassenstufe=1)
        Anmeldung.objects.create(schueler=p2, ag=self.ag1, prio=1)
        
        run_lottery()
        
        self.assertEqual(Anmeldung.objects.filter(ag=self.ag1, status='ACCEPTED').count(), 1)
        self.assertEqual(Anmeldung.objects.filter(ag=self.ag1, status='REJECTED').count(), 1)
        
        reset_lottery()
        self.assertEqual(Anmeldung.objects.filter(status='PENDING').count(), 2)

    def test_lottery_efficiency_large_group(self):
        # Create many profiles to ensure memory efficient query works correctly
        for i in range(50):
            u = User.objects.create(username=f"u{i}@test.de", email=f"u{i}@test.de")
            p = SchuelerProfile.objects.create(user=u, name=f"S{i}", klassenstufe=2)
            Anmeldung.objects.create(schueler=p, ag=self.ag1, prio=1)
            
        self.ag1.kapazitaet = 20
        self.ag1.save()
        run_lottery()
        
        self.assertEqual(Anmeldung.objects.filter(ag=self.ag1, status='ACCEPTED').count(), 20)
        self.assertEqual(Anmeldung.objects.filter(ag=self.ag1, status='REJECTED').count(), 30)
