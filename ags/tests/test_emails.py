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
        
        self.u2 = User.objects.create(username="kind2@test.de", email="kind2@test.de")
        self.p2 = SchuelerProfile.objects.create(user=self.u2, name="Kind 2", klassenstufe=2)
        Anmeldung.objects.create(schueler=self.p2, ag=self.ag1, prio=1, status='REJECTED')

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
        self.assertEqual(len(leader_mail.attachments), 3)
        
        # Verify all are PDFs
        for attachment in leader_mail.attachments:
            name, content, mime_type = attachment
            self.assertTrue(name.endswith('.pdf'))
            self.assertEqual(mime_type, 'application/pdf')
            self.assertTrue(content.startswith(b'%PDF-'))
            
        attachment_names = [a[0] for a in leader_mail.attachments]
        self.assertTrue(any('Abrechnung' in name for name in attachment_names))
        self.assertTrue(any('Teilnehmerliste' in name for name in attachment_names))
        self.assertTrue(any('Warteliste' in name for name in attachment_names))
