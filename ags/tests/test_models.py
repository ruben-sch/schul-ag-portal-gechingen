from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from ags.models import AG, SchuelerProfile, Anmeldung, AppConfig

class ModelTest(TestCase):
    def test_app_config_singleton(self):
        """Ensures that AppConfig only ever has one instance with pk=1."""
        config1 = AppConfig.load()
        config1.anmeldung_offen = True
        config1.save()
        
        config2 = AppConfig.load()
        self.assertEqual(config2.pk, 1)
        self.assertTrue(config2.anmeldung_offen)
        
        # Try to create another one
        config3 = AppConfig(pk=2, anmeldung_offen=False)
        config3.save()
        self.assertEqual(config3.pk, 1)
        
        self.assertEqual(AppConfig.objects.count(), 1)

    def test_grade_level_validation(self):
        """Ensures that students can only register for AGs matching their grade."""
        ag = AG.objects.create(
            name="Test AG", kapazitaet=10, 
            klassenstufe_min=1, klassenstufe_max=2, 
            status='APPROVED'
        )
        user = User.objects.create(username="test@test.de")
        profile = SchuelerProfile.objects.create(user=user, name="Kid", klassenstufe=4)
        
        anmeldung = Anmeldung(schueler=profile, ag=ag)
        with self.assertRaises(ValidationError):
            anmeldung.full_clean()

    def test_ag_str_and_details(self):
        ag = AG.objects.create(name="Robotik", kapazitaet=5, klassenstufe_min=1, klassenstufe_max=4)
        self.assertEqual(str(ag), "Robotik")
        self.assertEqual(ag.get_termine_display(), "Keine Termine")
        
        ag.termine = [{"datum": "2024-03-01", "start": "14:00", "ende": "15:00"}]
        self.assertEqual(ag.get_termine_display(), "01.03.2024 (14:00-15:00)")
