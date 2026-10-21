from django.test import TestCase, override_settings
from django.core import mail
from django.conf import settings
from django.contrib.auth.models import User
from ags.models import AG, SchuelerProfile, Anmeldung, AppConfig, TerminErinnerung
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


class LeaderPreviewEmailTest(TestCase):
    def setUp(self):
        self.ag = AG.objects.create(name="Schach AG", kapazitaet=5, klassenstufe_min=1, klassenstufe_max=4,
                                    status='APPROVED', ort='Raum 1', termine=[{'datum': '2026-11-03', 'start': '14:00', 'ende': '15:00'}],
                                    verantwortlicher_email='leiter@test.de', verantwortlicher_name='Frau Leiterin')
        AG.objects.create(name="Nicht genehmigt", kapazitaet=5, klassenstufe_min=1, klassenstufe_max=4,
                          verantwortlicher_email='x@test.de', verantwortlicher_name='X')
        u = User.objects.create(username="kind@test.de", email="kind@test.de")
        p = SchuelerProfile.objects.create(user=u, name="Kind A", klassenstufe=2)
        Anmeldung.objects.create(schueler=p, ag=self.ag, prio=1, status='ACCEPTED')

    def test_preview_mail_content_without_attachments(self):
        from ags.emails import send_leader_preview_emails
        mail.outbox = []
        result = send_leader_preview_emails()
        self.assertEqual(result, {'sent': 1, 'failed': 0})
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['leiter@test.de'])
        self.assertIn('Vorläufige', msg.subject)
        self.assertEqual(msg.attachments, [])
        html = msg.alternatives[0][0]
        self.assertIn('Kind A', html)
        self.assertIn('03.11.2026', html)
        self.assertIn('Raum 1', html)
        self.ag.refresh_from_db()
        self.assertTrue(self.ag.leader_preview_sent)
        self.assertFalse(self.ag.leader_email_sent)

    def test_only_unsent_and_reset_by_lottery(self):
        from ags.emails import send_leader_preview_emails
        from ags.utils import run_lottery
        send_leader_preview_emails()
        mail.outbox = []
        self.assertEqual(send_leader_preview_emails(), {'sent': 0, 'failed': 0})
        run_lottery()
        self.ag.refresh_from_db()
        self.assertFalse(self.ag.leader_preview_sent)

    def test_bulk_view_enqueues_preview(self):
        from django.urls import reverse
        admin = User.objects.create(username="admin@test.de", is_staff=True)
        self.client.force_login(admin)
        mail.outbox = []
        self.client.post(reverse('send_bulk_emails'), {'target': 'leader_preview'})
        self.assertEqual(len(mail.outbox), 1)
        self.client.post(reverse('resend_leader_email'), {'ag_id': self.ag.id, 'kind': 'preview'})
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('Vorläufige', mail.outbox[1].subject)

    def test_blocked_before_lottery(self):
        from django.urls import reverse
        from ags.emails import send_leader_preview_emails, send_single_leader_preview_email
        Anmeldung.objects.update(status='PENDING')
        mail.outbox = []
        self.assertEqual(send_leader_preview_emails(), {'sent': 0, 'failed': 0})
        self.assertIsNone(send_single_leader_preview_email(self.ag))
        admin = User.objects.create(username="admin@test.de", is_staff=True)
        self.client.force_login(admin)
        response = self.client.post(reverse('send_bulk_emails'), {'target': 'leader_preview'}, follow=True)
        self.assertContains(response, 'erst nach der Auslosung')
        self.client.post(reverse('resend_leader_email'), {'ag_id': self.ag.id, 'kind': 'preview'})
        self.assertEqual(len(mail.outbox), 0)
        self.ag.refresh_from_db()
        self.assertFalse(self.ag.leader_preview_sent)

    def test_skipped_after_final_list(self):
        from ags.emails import send_leader_preview_emails
        AG.objects.filter(id=self.ag.id).update(leader_email_sent=True)
        mail.outbox = []
        self.assertEqual(send_leader_preview_emails(only_unsent=False), {'sent': 0, 'failed': 0})
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_lottery_resets_flag(self):
        from ags.emails import send_leader_preview_emails
        from ags.utils import reset_lottery
        send_leader_preview_emails()
        reset_lottery()
        self.ag.refresh_from_db()
        self.assertFalse(self.ag.leader_preview_sent)

    def test_non_staff_cannot_send(self):
        from django.urls import reverse
        user = User.objects.create(username="eltern@test.de")
        self.client.force_login(user)
        mail.outbox = []
        response = self.client.post(reverse('send_bulk_emails'), {'target': 'leader_preview'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
        self.client.post(reverse('resend_leader_email'), {'ag_id': self.ag.id, 'kind': 'preview'})
        self.assertEqual(len(mail.outbox), 0)

    def test_smtp_error_keeps_flag_false(self):
        from unittest import mock
        import smtplib
        from ags.emails import send_leader_preview_emails
        with mock.patch('ags.emails._senden', side_effect=smtplib.SMTPRecipientsRefused({})):
            self.assertEqual(send_leader_preview_emails(), {'sent': 0, 'failed': 1})
        self.ag.refresh_from_db()
        self.assertFalse(self.ag.leader_preview_sent)

    def test_new_lottery_during_send_is_not_marked_sent(self):
        from unittest import mock
        from ags.emails import send_single_leader_preview_email

        def neue_losung(msg):
            Anmeldung.objects.update(status='REJECTED')

        with mock.patch('ags.emails._senden', side_effect=neue_losung):
            self.assertFalse(send_single_leader_preview_email(self.ag))
        self.ag.refresh_from_db()
        self.assertFalse(self.ag.leader_preview_sent)

    def test_multiline_fields_keep_line_breaks(self):
        from ags.emails import send_single_leader_preview_email
        self.ag.mitzubringen = "Sportzeug\nTrinkflasche"
        self.ag.save()
        mail.outbox = []
        send_single_leader_preview_email(self.ag)
        self.assertIn('Sportzeug<br>Trinkflasche', mail.outbox[0].alternatives[0][0])

class TerminReminderTest(TestCase):
    def setUp(self):
        from datetime import date
        self.heute = date(2026, 11, 1)
        self.ag = AG.objects.create(name="Tanz AG", kapazitaet=5, klassenstufe_min=1, klassenstufe_max=4, status='APPROVED',
                                    ort='Aula', mitzubringen='Turnschuhe',
                                    termine=[{'datum': '2026-11-03', 'start': '14:00', 'ende': '15:00'},
                                             {'datum': '2026-11-10', 'start': '14:00', 'ende': '15:00'},
                                             {'datum': 'kaputt'}],
                                    verantwortlicher_email='l@test.de', verantwortlicher_name='Frau Tanz')
        u = User.objects.create(username="eltern@test.de", email="eltern@test.de")
        p = SchuelerProfile.objects.create(user=u, name="Kind", klassenstufe=2, acceptance_email_sent=True)
        self.anm = Anmeldung.objects.create(schueler=p, ag=self.ag, prio=1, status='ACCEPTED')
        u2 = User.objects.create(username="warte@test.de", email="warte@test.de")
        p2 = SchuelerProfile.objects.create(user=u2, name="Wartend", klassenstufe=2)
        Anmeldung.objects.create(schueler=p2, ag=self.ag, prio=1, status='REJECTED')

    def test_reminder_two_days_before_only_once(self):
        from ags.emails import send_termin_reminders
        mail.outbox = []
        self.assertEqual(send_termin_reminders(heute=self.heute), {'sent': 1, 'failed': 0, 'abgebrochen': False})
        self.assertEqual(mail.outbox[0].to, ['eltern@test.de'])
        self.assertIn('03.11.2026', mail.outbox[0].subject)
        html = mail.outbox[0].alternatives[0][0]
        self.assertIn('Aula', html)
        self.assertIn('Turnschuhe', html)
        self.assertEqual(send_termin_reminders(heute=self.heute)['sent'], 0)

    def test_catch_up_day_before_but_not_after(self):
        from datetime import timedelta
        from ags.emails import send_termin_reminders
        self.assertEqual(send_termin_reminders(heute=self.heute + timedelta(days=1))['sent'], 1)
        self.assertEqual(send_termin_reminders(heute=self.heute + timedelta(days=2))['sent'], 0)

    def test_nothing_when_termin_far_away(self):
        from datetime import timedelta
        from ags.emails import send_termin_reminders
        self.assertEqual(send_termin_reminders(heute=self.heute - timedelta(days=1))['sent'], 0)

    def test_failed_send_is_retried_next_run(self):
        from unittest import mock
        from django.core.mail.backends.locmem import EmailBackend
        from ags.emails import send_termin_reminders
        with mock.patch.object(EmailBackend, 'send_messages', side_effect=TimeoutError()):
            self.assertEqual(send_termin_reminders(heute=self.heute), {'sent': 0, 'failed': 1, 'abgebrochen': True})
        self.assertFalse(TerminErinnerung.objects.exists())
        self.assertEqual(send_termin_reminders(heute=self.heute)['sent'], 1)

    def test_temporary_error_aborts_run(self):
        from unittest import mock
        from django.core.mail.backends.locmem import EmailBackend
        from ags.emails import send_termin_reminders
        u = User.objects.create(username="zwei@test.de", email="zwei@test.de")
        p = SchuelerProfile.objects.create(user=u, name="Zwei", klassenstufe=2, acceptance_email_sent=True)
        Anmeldung.objects.create(schueler=p, ag=self.ag, prio=1, status='ACCEPTED')
        with mock.patch.object(EmailBackend, 'send_messages', side_effect=TimeoutError()) as send:
            send_termin_reminders(heute=self.heute)
        self.assertEqual(send.call_count, 1)

    def test_permanent_error_is_not_retried(self):
        from unittest import mock
        import smtplib
        from django.core.mail.backends.locmem import EmailBackend
        from ags.emails import send_termin_reminders
        error = smtplib.SMTPDataError(550, b"Mailbox unavailable")
        with mock.patch.object(EmailBackend, 'send_messages', side_effect=error):
            self.assertEqual(send_termin_reminders(heute=self.heute)['failed'], 1)
        self.assertTrue(TerminErinnerung.objects.get().fehlgeschlagen)
        mail.outbox = []
        self.assertEqual(send_termin_reminders(heute=self.heute)['sent'], 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_claimed_reminder_is_skipped(self):
        from ags.emails import send_single_termin_reminder
        from datetime import date
        TerminErinnerung.objects.create(anmeldung=self.anm, datum=date(2026, 11, 3))
        mail.outbox = []
        self.assertIsNone(send_single_termin_reminder(self.anm, date(2026, 11, 3), {}))
        self.assertEqual(len(mail.outbox), 0)

    def test_no_reminder_before_acceptance_email(self):
        from ags.emails import send_termin_reminders
        SchuelerProfile.objects.update(acceptance_email_sent=False)
        self.assertEqual(send_termin_reminders(heute=self.heute)['sent'], 0)

    def test_no_reminder_for_unapproved_ag(self):
        from ags.emails import send_termin_reminders
        AG.objects.filter(id=self.ag.id).update(status='SUBMITTED')
        self.assertEqual(send_termin_reminders(heute=self.heute)['sent'], 0)

    def test_legacy_string_termine_are_ignored(self):
        from ags.emails import send_termin_reminders
        AG.objects.filter(id=self.ag.id).update(termine="Dienstags 14 Uhr")
        self.assertEqual(send_termin_reminders(heute=self.heute)['sent'], 0)

    def test_command_respects_earliest_hour(self):
        from io import StringIO
        from unittest import mock
        from django.core.management import call_command
        from django.test import override_settings
        out = StringIO()
        with override_settings(REMINDER_EARLIEST_HOUR=25):
            call_command('send_reminders', stdout=out)
        self.assertIn('keine Erinnerungen', out.getvalue())
        with mock.patch('ags.emails.timezone.localdate', return_value=self.heute):
            out = StringIO()
            call_command('send_reminders', '--sofort', stdout=out)
        self.assertIn('1 gesendet', out.getvalue())

    def test_admin_is_read_only(self):
        from django.urls import reverse
        admin = User.objects.create(username="su@test.de", is_staff=True, is_superuser=True)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse('admin:ags_terminerinnerung_add')).status_code, 403)
        self.assertEqual(self.client.get(reverse('admin:ags_terminerinnerung_changelist')).status_code, 200)
