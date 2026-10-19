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


class EmailRetryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="kind@test.de", email="kind@test.de")
        self.profile = SchuelerProfile.objects.create(user=self.user, name="Kind", klassenstufe=2)

    def test_transient_error_is_retried(self):
        from unittest import mock
        import smtplib
        from django.core.mail.backends.locmem import EmailBackend
        from ags.emails import send_registration_confirmation

        original = EmailBackend.send_messages
        calls = []

        def flaky(backend, messages):
            calls.append(1)
            if len(calls) == 1:
                raise smtplib.SMTPServerDisconnected("Verbindung verloren")
            return original(backend, messages)

        mail.outbox = []
        with mock.patch.object(EmailBackend, 'send_messages', flaky):
            self.assertTrue(send_registration_confirmation(self.profile))
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(mail.outbox), 1)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.confirmation_email_sent)

    def test_permanent_error_is_not_retried(self):
        from unittest import mock
        import smtplib
        from django.core.mail.backends.locmem import EmailBackend
        from ags.emails import send_registration_confirmation

        error = smtplib.SMTPDataError(550, b"Mailbox unavailable")
        with mock.patch.object(EmailBackend, 'send_messages', side_effect=error) as send:
            self.assertFalse(send_registration_confirmation(self.profile))
        self.assertEqual(send.call_count, 1)
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.confirmation_email_sent)

    def test_gives_up_after_max_attempts(self):
        from unittest import mock
        from django.core.mail.backends.locmem import EmailBackend
        from ags.emails import send_registration_confirmation, MAX_VERSUCHE

        with mock.patch.object(EmailBackend, 'send_messages', side_effect=TimeoutError()) as send:
            self.assertFalse(send_registration_confirmation(self.profile))
        self.assertEqual(send.call_count, MAX_VERSUCHE)

    def test_bulk_send_uses_single_connection(self):
        from unittest import mock
        ag = AG.objects.create(name="AG", kapazitaet=5, klassenstufe_min=1, klassenstufe_max=4, status='APPROVED',
                               verantwortlicher_email='leiter@test.de', verantwortlicher_name='Leiter')
        for i in range(3):
            u = User.objects.create(username=f"k{i}@test.de", email=f"k{i}@test.de")
            p = SchuelerProfile.objects.create(user=u, name=f"K{i}", klassenstufe=2)
            Anmeldung.objects.create(schueler=p, ag=ag, prio=1, status='ACCEPTED')

        with mock.patch('ags.emails.get_connection', wraps=__import__('django.core.mail').core.mail.get_connection) as gc:
            mail.outbox = []
            result = send_allocation_emails()
        self.assertEqual(gc.call_count, 1)
        self.assertEqual(result['students_sent'], 3)
        self.assertEqual(result['leaders_sent'], 1)
        self.assertEqual(len(mail.outbox), 4)
