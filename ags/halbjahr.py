"""
Halbjahres-Workflow: welche Aktion im aktuellen Stand des Halbjahres erlaubt ist, und die geschützten Aktionen selbst.

Die Phase wird bei jedem Aufruf aus den vorhandenen Feldern abgeleitet und nicht gespeichert.
"""
import io
from collections.abc import Callable
from dataclasses import dataclass

from django.core.management import call_command
from django.db import transaction

from . import utils
from .models import AG, Anmeldung, AppConfig, SchuelerProfile

BESTAETIGUNG = "NEUES HALBJAHR"

ANMELDUNG_OFFEN = "Die Anmeldung ist noch offen. Bitte zuerst die Anmeldung schließen, dann auslosen."
# Eine neue Zuteilung würde nie verschickt (nur ungesendete Mails gehen raus), Eltern behielten die alte.
ENDGUELTIG_VERSCHICKT = ("Die endgültigen Mails wurden bereits verschickt. Eine neue Auslosung würde die verschickten "
                         "Zuteilungen ungültig machen; Änderungen bitte über die manuelle Korrektur.")
NICHT_AUSGELOST = "Noch nicht ausgelost."
VORSCHAU_VOR_AUSLOSUNG = "Vorläufige Listen gibt es erst nach der Auslosung."


class Gesperrt(Exception):
    """Die Aktion ist im aktuellen Stand nicht erlaubt; str() ist der Grund für die Anzeige."""


@dataclass(frozen=True)
class Phase:
    """Momentaufnahme des Halbjahres. Jedes *_gesperrt-Feld ist "" (erlaubt) oder der Grund für die Sperre."""
    ausgelost: bool
    auslosen_gesperrt: str
    zuruecksetzen_gesperrt: str
    vorschau_gesperrt: str

    def vorschau_gesperrt_fuer(self, ag: AG) -> str:
        """Wie vorschau_gesperrt, zusätzlich gesperrt, wenn diese AG ihre endgültige Liste schon hat."""
        if self.vorschau_gesperrt:
            return self.vorschau_gesperrt
        if ag.leader_email_sent:
            return f"Für {ag.name} wurde die endgültige Liste bereits verschickt."
        return ""


def phase() -> Phase:
    ausgelost = Anmeldung.objects.exclude(status=Anmeldung.Status.PENDING).exists()
    # Vorläufige Listen nur, wenn alle Anmeldungen ausgelost sind und es überhaupt Zusagen gibt.
    listen_stehen = (not Anmeldung.objects.filter(status=Anmeldung.Status.PENDING).exists()
                     and Anmeldung.objects.filter(status=Anmeldung.Status.ACCEPTED).exists())
    if AppConfig.load().anmeldung_offen:
        zuteilung_gesperrt = ANMELDUNG_OFFEN
    elif (AG.objects.filter(leader_email_sent=True).exists()
          or SchuelerProfile.objects.filter(acceptance_email_sent=True).exists()):
        zuteilung_gesperrt = ENDGUELTIG_VERSCHICKT
    else:
        zuteilung_gesperrt = ""
    return Phase(
        ausgelost=ausgelost,
        auslosen_gesperrt=zuteilung_gesperrt,
        zuruecksetzen_gesperrt=zuteilung_gesperrt or ("" if ausgelost else NICHT_AUSGELOST),
        vorschau_gesperrt="" if listen_stehen else VORSCHAU_VOR_AUSLOSUNG,
    )


def sperren() -> None:
    """Sperrt die Konfigurationszeile bis zum Ende der Transaktion: gleichzeitige Aktionen laufen nacheinander.

    Nur innerhalb von transaction.atomic aufrufen. Auch wer ein Flag schreibt, das von der Zuteilung abhängt, sperrt hier.
    """
    AppConfig.load()
    AppConfig.objects.select_for_update().get(pk=1)


def _ausfuehren(aktion: Callable[[], None], sperrgrund: Callable[[Phase], str] | None = None) -> None:
    """Führt eine Aktion unter der Sperre aus; mit sperrgrund nur, wenn sie im aktuellen Stand erlaubt ist, sonst Gesperrt."""
    with transaction.atomic():
        sperren()
        # Unter der Sperre neu prüfen: Die Phase, die die Seite angezeigt hat, kann veraltet sein.
        if sperrgrund and (grund := sperrgrund(phase())):
            raise Gesperrt(grund)
        aktion()


def auslosen() -> None:
    _ausfuehren(utils.run_lottery, lambda p: p.auslosen_gesperrt)


def zuruecksetzen() -> None:
    _ausfuehren(utils.reset_lottery, lambda p: p.zuruecksetzen_gesperrt)


def neues_halbjahr(bestaetigung: str) -> None:
    if bestaetigung != BESTAETIGUNG:
        raise Gesperrt(f"Bitte zur Bestätigung {BESTAETIGUNG} eingeben.")
    # Eine Transaktion: Bricht der Lauf ab, bleibt kein halb gelöschter Zustand. Die Sperre serialisiert
    # Doppelklicks; der zweite Lauf findet dann nichts mehr zum Archivieren. Die Ausgabe des Commands
    # (inkl. JSON-Dump mit personenbezogenen Daten) landet bewusst nicht im Log.
    _ausfuehren(lambda: call_command('next_semester', stdout=io.StringIO()))
