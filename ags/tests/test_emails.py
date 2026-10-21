from django.test import TestCase, override_settings
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


def _smtp_mock():
    """Ersetzt smtplib.SMTP: zählt Verbindungsaufbauten und nimmt jede Mail an."""
    from unittest import mock
    smtp_class = mock.MagicMock()
    smtp_class.return_value.noop.return_value = (250, b"OK")
    smtp_class.return_value.sendmail.return_value = {}
    smtp_class.return_value.send_message.return_value = {}
    return smtp_class


class EmailRetryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="kind@test.de", email="kind@test.de")
        self.profile = SchuelerProfile.objects.create(user=self.user, name="Kind", klassenstufe=2)

    def _bulk_daten(self, anzahl=3):
        ag = AG.objects.create(name="AG", kapazitaet=5, klassenstufe_min=1, klassenstufe_max=4, status='APPROVED',
                               verantwortlicher_email='leiter@test.de', verantwortlicher_name='Leiter')
        for i in range(anzahl):
            u = User.objects.create(username=f"k{i}@test.de", email=f"k{i}@test.de")
            p = SchuelerProfile.objects.create(user=u, name=f"K{i}", klassenstufe=2)
            Anmeldung.objects.create(schueler=p, ag=ag, prio=1, status='ACCEPTED')
        return ag

    def test_rejected_message_is_retried(self):
        from unittest import mock
        import smtplib
        from django.core.mail.backends.locmem import EmailBackend
        from ags.emails import send_registration_confirmation

        original = EmailBackend.send_messages
        calls = []

        def flaky(backend, messages):
            calls.append(1)
            if len(calls) == 1:
                raise smtplib.SMTPDataError(451, b"Try again later")
            return original(backend, messages)

        mail.outbox = []
        with mock.patch.object(EmailBackend, 'send_messages', flaky):
            self.assertTrue(send_registration_confirmation(self.profile))
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(mail.outbox), 1)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.confirmation_email_sent)

    def test_connect_error_is_retried(self):
        from unittest import mock
        import smtplib
        from django.core.mail.backends.locmem import EmailBackend
        from ags.emails import send_registration_confirmation

        mail.outbox = []
        with mock.patch.object(EmailBackend, 'open', side_effect=[smtplib.SMTPConnectError(421, b"busy"), True]):
            self.assertTrue(send_registration_confirmation(self.profile))
        self.assertEqual(len(mail.outbox), 1)

    def test_timeout_while_sending_is_not_retried(self):
        # Der Server kann die Mail schon angenommen haben; ein zweiter Versuch käme doppelt an.
        from unittest import mock
        from django.core.mail.backends.locmem import EmailBackend
        from ags.emails import send_registration_confirmation

        with mock.patch.object(EmailBackend, 'send_messages', side_effect=TimeoutError()) as send:
            self.assertFalse(send_registration_confirmation(self.profile))
        self.assertEqual(send.call_count, 1)

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

        with mock.patch.object(EmailBackend, 'open', side_effect=TimeoutError()) as open_, \
                mock.patch.object(EmailBackend, 'send_messages') as send:
            self.assertFalse(send_registration_confirmation(self.profile))
        self.assertEqual(open_.call_count, MAX_VERSUCHE)
        send.assert_not_called()

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend', DEFAULT_FROM_EMAIL='portal@test.de')
    def test_bulk_send_reuses_one_smtp_connection(self):
        from unittest import mock
        self._bulk_daten()
        smtp_class = _smtp_mock()
        with mock.patch('smtplib.SMTP', smtp_class):
            result = send_allocation_emails()
        self.assertEqual(result['students_sent'], 3)
        self.assertEqual(result['leaders_sent'], 1)
        self.assertEqual(smtp_class.call_count, 1)
        smtp_class.return_value.quit.assert_called_once()

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend', DEFAULT_FROM_EMAIL='portal@test.de')
    def test_bulk_send_reconnects_after_server_disconnect(self):
        from unittest import mock
        import smtplib
        self._bulk_daten()
        smtp_class = _smtp_mock()
        smtp_class.return_value.noop.side_effect = [(250, b"OK"), smtplib.SMTPServerDisconnected(), (250, b"OK"), (250, b"OK")]
        with mock.patch('smtplib.SMTP', smtp_class):
            result = send_allocation_emails()
        self.assertEqual(result['students_sent'] + result['leaders_sent'], 4)
        self.assertEqual(smtp_class.call_count, 2)

    def test_send_does_not_overwrite_concurrent_changes(self):
        from ags.emails import send_single_acceptance_email
        veraltet = SchuelerProfile.objects.get(id=self.profile.id)
        SchuelerProfile.objects.filter(id=self.profile.id).update(klassenstufe=4)
        self.assertTrue(send_single_acceptance_email(veraltet, ag_list=[]))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.klassenstufe, 4)
        self.assertTrue(self.profile.acceptance_email_sent)


class EmailTaskTest(TestCase):
    def setUp(self):
        self.ag = AG.objects.create(name="AG", kapazitaet=20, klassenstufe_min=1, klassenstufe_max=4, status='APPROVED',
                                    verantwortlicher_email='leiter@test.de', verantwortlicher_name='Leiter')
        self.profile = None
        for i in range(12):
            u = User.objects.create(username=f"k{i}@test.de", email=f"k{i}@test.de")
            p = SchuelerProfile.objects.create(user=u, name=f"K{i}", klassenstufe=2)
            Anmeldung.objects.create(schueler=p, ag=self.ag, prio=1, status='ACCEPTED')
            self.profile = self.profile or p

    def test_bulk_task_sends_in_batches(self):
        from unittest import mock
        from ags import tasks
        mail.outbox = []
        with mock.patch('ags.tasks.send_acceptance_batch_task', wraps=tasks.send_acceptance_batch_task) as batch:
            result = tasks.send_allocation_emails_task.enqueue(only_unsent=True)
        self.assertEqual(result.return_value, 3)  # 2 Schüler-Pakete (10 + 2) und 1 Leiter-Paket
        self.assertEqual(batch.enqueue.call_count, 2)
        self.assertEqual(len(mail.outbox), 13)
        self.assertFalse(SchuelerProfile.objects.filter(acceptance_email_sent=False).exists())

    def test_failed_mail_marks_task_failed(self):
        from unittest import mock
        import smtplib
        from django.core.mail.backends.locmem import EmailBackend
        from django.tasks import TaskResultStatus
        from ags import tasks

        error = smtplib.SMTPDataError(550, b"Mailbox unavailable")
        with mock.patch.object(EmailBackend, 'send_messages', side_effect=error):
            einzel = tasks.send_acceptance_email_task.enqueue(self.profile.id)
            paket = tasks.send_acceptance_batch_task.enqueue([self.profile.id])
        self.assertEqual(einzel.status, TaskResultStatus.FAILED)
        self.assertEqual(paket.status, TaskResultStatus.FAILED)
        self.assertIn("EmailVersandFehler", einzel.errors[0].exception_class_path)

    def test_admin_action_enqueues_instead_of_sending(self):
        from unittest import mock
        from ags import admin as ags_admin
        modeladmin = mock.MagicMock()
        mail.outbox = []
        with mock.patch('ags.admin.send_allocation_emails_task') as task:
            ags_admin.trigger_emails(modeladmin, mock.MagicMock(), AG.objects.none())
        task.enqueue.assert_called_once_with(only_unsent=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_enqueue_failure_keeps_registration(self):
        from unittest import mock
        from ags import services
        with mock.patch('ags.tasks.send_registration_confirmation_task') as task:
            task.enqueue.side_effect = RuntimeError("DB weg")
            with self.captureOnCommitCallbacks(execute=True):
                services.update_student_registrations(self.profile, [self.ag.id])
        task.enqueue.assert_called_once_with(self.profile.id)
        self.assertTrue(Anmeldung.objects.filter(schueler=self.profile, ag=self.ag).exists())
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.confirmation_email_sent)
