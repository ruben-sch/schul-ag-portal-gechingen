from django.test import TestCase
from django.core import mail
from django.conf import settings
from django.contrib.auth.models import User
from ags.models import AG, SchuelerProfile, Anmeldung, AppConfig
from ags.emails import send_allocation_emails

class EmailTest(TestCase):
    def setUp(self):
        AppConfig.load().save()
        self.ag1 = AG.objects.create(
            name="Roboter AG",
            kapazitaet=1,
            kosten=10,
            klassenstufe_min=1,
            klassenstufe_max=4,
            status='APPROVED',
            verantwortlicher_email='leiter@test.de',
            verantwortlicher_name='Herr Leiter'
        )
        self.u1 = User.objects.create(username="kind1@test.de", email="kind1@test.de")
        self.p1 = SchuelerProfile.objects.create(user=self.u1, name="Kind 1", klassenstufe=2)
        Anmeldung.objects.create(schueler=self.p1, ag=self.ag1, prio=1, status='ACCEPTED')

    def test_send_allocation_emails_with_attachment(self):
        # Empty the test outbox
        mail.outbox = []

        # Send emails
        send_allocation_emails()

        # Two emails should be sent: one to the student, one to the AG leader
        self.assertEqual(len(mail.outbox), 2)
        
        student_mail = mail.outbox[0]
        leader_mail = mail.outbox[1]
        
        if student_mail.to[0] == 'leiter@test.de':
            # Swap if the order is different
            leader_mail, student_mail = student_mail, leader_mail
            
        self.assertEqual(leader_mail.to, ['leiter@test.de'])
        
        # Check attachment
        self.assertEqual(len(leader_mail.attachments), 1)
        attachment = leader_mail.attachments[0]
        
        # Name should be Abrechnung_Roboter AG.csv
        self.assertIn('Abrechnung', attachment[0])
        self.assertTrue(attachment[0].endswith('.csv'))
        
        # Content should have the required columns
        # Einnahmen Teilnehmergebühren, Ausgaben (mehrere Zeilen), Summe
        content = attachment[1]
        # Should be a string or bytes
        if isinstance(content, bytes):
            content = content.decode('utf-8')
            
        self.assertIn('Einnahmen', content)
        self.assertIn('Ausgaben', content)
        self.assertIn('Summe', content)
