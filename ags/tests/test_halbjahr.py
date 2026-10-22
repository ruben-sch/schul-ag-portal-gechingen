import os
import tempfile

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from ags import halbjahr
from ags.models import AG, Anmeldung, AppConfig, ArchivEintrag, SchuelerProfile


class HalbjahrTest(TestCase):
    def setUp(self):
        self.ag = AG.objects.create(name="Fußball AG", kapazitaet=1, klassenstufe_min=1, klassenstufe_max=4,
                                    status=AG.Status.APPROVED, verantwortlicher_email='l@test.de',
                                    verantwortlicher_name='L')
        user = User.objects.create(username="eltern@test.de", email="eltern@test.de")
        self.profil = SchuelerProfile.objects.create(user=user, name="Kind", klassenstufe=2)
        self.anmeldung = Anmeldung.objects.create(schueler=self.profil, ag=self.ag, prio=1)

    def test_auslosen_gesperrt_solange_anmeldung_offen(self):
        AppConfig.load()
        AppConfig.objects.update(anmeldung_offen=True)
        self.assertIn("Anmeldung ist noch offen", halbjahr.phase().auslosen_gesperrt)

    def test_auslosen_erlaubt_nach_anmeldeschluss(self):
        self.assertEqual(halbjahr.phase().auslosen_gesperrt, "")

    def test_auslosen_gesperrt_nach_zuteilungsmail(self):
        SchuelerProfile.objects.update(acceptance_email_sent=True)
        self.assertIn("bereits verschickt", halbjahr.phase().auslosen_gesperrt)

    def test_auslosen_gesperrt_nach_endgueltiger_leiterliste(self):
        AG.objects.update(leader_email_sent=True)
        self.assertIn("bereits verschickt", halbjahr.phase().auslosen_gesperrt)

    def test_zuruecksetzen_gesperrt_vor_auslosung(self):
        self.assertIn("Noch nicht ausgelost", halbjahr.phase().zuruecksetzen_gesperrt)

    def test_zuruecksetzen_gesperrt_nach_zuteilungsmail(self):
        Anmeldung.objects.update(status=Anmeldung.Status.ACCEPTED)
        SchuelerProfile.objects.update(acceptance_email_sent=True)
        self.assertIn("bereits verschickt", halbjahr.phase().zuruecksetzen_gesperrt)

    def test_zuruecksetzen_gesperrt_solange_anmeldung_offen(self):
        Anmeldung.objects.update(status=Anmeldung.Status.ACCEPTED)
        AppConfig.load()
        AppConfig.objects.update(anmeldung_offen=True)
        self.assertIn("Anmeldung ist noch offen", halbjahr.phase().zuruecksetzen_gesperrt)

    def test_zuruecksetzen_erlaubt_nach_auslosung(self):
        Anmeldung.objects.update(status=Anmeldung.Status.REJECTED)
        phase = halbjahr.phase()
        self.assertTrue(phase.ausgelost)
        self.assertEqual(phase.zuruecksetzen_gesperrt, "")

    def test_vorschau_gesperrt_vor_auslosung(self):
        self.assertIn("erst nach der Auslosung", halbjahr.phase().vorschau_gesperrt)

    def test_vorschau_gesperrt_ohne_zusage(self):
        Anmeldung.objects.update(status=Anmeldung.Status.REJECTED)
        self.assertIn("erst nach der Auslosung", halbjahr.phase().vorschau_gesperrt)

    def test_vorschau_gesperrt_bei_neuer_anmeldung_nach_auslosung(self):
        Anmeldung.objects.update(status=Anmeldung.Status.ACCEPTED)
        ag2 = AG.objects.create(name="Schach AG", kapazitaet=5, klassenstufe_min=1, klassenstufe_max=4,
                                status=AG.Status.APPROVED, verantwortlicher_email='s@test.de', verantwortlicher_name='S')
        Anmeldung.objects.create(schueler=self.profil, ag=ag2, prio=2)
        self.assertIn("erst nach der Auslosung", halbjahr.phase().vorschau_gesperrt)

    def test_vorschau_erlaubt_nach_auslosung(self):
        Anmeldung.objects.update(status=Anmeldung.Status.ACCEPTED)
        self.assertEqual(halbjahr.phase().vorschau_gesperrt, "")

    def test_vorschau_fuer_ag_gesperrt_nach_endgueltiger_liste(self):
        Anmeldung.objects.update(status=Anmeldung.Status.ACCEPTED)
        AG.objects.update(leader_email_sent=True)
        self.ag.refresh_from_db()
        self.assertIn("endgültige Liste bereits verschickt", halbjahr.phase().vorschau_gesperrt_fuer(self.ag))

    def test_vorschau_fuer_ag_gesperrt_vor_auslosung(self):
        self.assertIn("erst nach der Auslosung", halbjahr.phase().vorschau_gesperrt_fuer(self.ag))

    def test_vorschau_fuer_ag_erlaubt_nach_auslosung(self):
        Anmeldung.objects.update(status=Anmeldung.Status.ACCEPTED)
        self.assertEqual(halbjahr.phase().vorschau_gesperrt_fuer(self.ag), "")

    def test_auslosen_teilt_zu(self):
        halbjahr.auslosen()
        self.assertEqual(Anmeldung.objects.get().status, Anmeldung.Status.ACCEPTED)

    def test_auslosen_gesperrt_wirft_und_teilt_nicht_zu(self):
        SchuelerProfile.objects.update(acceptance_email_sent=True)
        with self.assertRaisesMessage(halbjahr.Gesperrt, "bereits verschickt"):
            halbjahr.auslosen()
        self.assertEqual(Anmeldung.objects.get().status, Anmeldung.Status.PENDING)

    def test_zuruecksetzen_setzt_auf_wartend(self):
        Anmeldung.objects.update(status=Anmeldung.Status.ACCEPTED)
        halbjahr.zuruecksetzen()
        self.assertEqual(Anmeldung.objects.get().status, Anmeldung.Status.PENDING)
        self.assertFalse(halbjahr.phase().ausgelost)

    def test_zuruecksetzen_nach_zuteilungsmail_wirft(self):
        Anmeldung.objects.update(status=Anmeldung.Status.ACCEPTED)
        SchuelerProfile.objects.update(acceptance_email_sent=True)
        with self.assertRaisesMessage(halbjahr.Gesperrt, "bereits verschickt"):
            halbjahr.zuruecksetzen()
        self.assertEqual(Anmeldung.objects.get().status, Anmeldung.Status.ACCEPTED)

    def test_neues_halbjahr_ohne_bestaetigung_wirft_und_loescht_nichts(self):
        with self.assertRaisesMessage(halbjahr.Gesperrt, "NEUES HALBJAHR"):
            halbjahr.neues_halbjahr("ja")
        self.assertEqual(AG.objects.count(), 1)

    def test_neues_halbjahr_archiviert_und_setzt_zurueck(self):
        AppConfig.load()
        AppConfig.objects.update(ag_registrierung_offen=False)
        with tempfile.TemporaryDirectory() as backup_dir, override_settings(SEMESTER_BACKUP_DIR=backup_dir):
            halbjahr.neues_halbjahr(halbjahr.BESTAETIGUNG)
            self.assertEqual(len(os.listdir(backup_dir)), 1)
        self.assertEqual(AG.objects.count(), 0)
        self.assertEqual(ArchivEintrag.objects.count(), 1)
        self.assertTrue(AppConfig.load().ag_registrierung_offen)

    def test_neues_halbjahr_schreibt_keine_personendaten_ins_log(self):
        import contextlib
        import io
        ausgabe = io.StringIO()
        with tempfile.TemporaryDirectory() as backup_dir, override_settings(SEMESTER_BACKUP_DIR=backup_dir), \
                contextlib.redirect_stdout(ausgabe):
            halbjahr.neues_halbjahr(halbjahr.BESTAETIGUNG)
        self.assertNotIn("l@test.de", ausgabe.getvalue())

    def test_neues_halbjahr_bricht_ohne_halben_zustand_ab(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as backup_dir, override_settings(SEMESTER_BACKUP_DIR=backup_dir), \
                mock.patch('django.contrib.auth.models.User.objects.filter', side_effect=RuntimeError("Abbruch")):
            with self.assertRaises(RuntimeError):
                halbjahr.neues_halbjahr(halbjahr.BESTAETIGUNG)
        self.assertEqual(AG.objects.count(), 1)
        self.assertEqual(ArchivEintrag.objects.count(), 0)
