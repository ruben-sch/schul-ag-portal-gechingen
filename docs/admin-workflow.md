# Admin-Handbuch: Ablauf eines Halbjahres

Dieses Handbuch beschreibt, wie ein Halbjahr im AG-Portal von der AG-Eingabe bis zum Versand der Zusagen läuft.
Alle Schritte findest du im Admin-Bereich unter **Statistik & Losverfahren → Tab „Workflow“** (`/stats/`).
Der Tab ist in vier Phasen gegliedert, die du von oben nach unten abarbeitest.

## Phase 1: Neues Halbjahr starten

1. **Neues Halbjahr starten:** `NEUES HALBJAHR` in das Feld tippen und den Button drücken.
   - Alle Anmeldungen der laufenden Runde werden ins Archiv übernommen (Django-Admin → „Archiv-Einträge“).
   - Danach werden **alle AGs, Schüler, Anmeldungen und Eltern-Konten gelöscht**. Admin- und Staff-Konten bleiben erhalten.
   - Zusätzlich landet ein JSON-Backup in den Server-Logs. Das ist dieselbe Funktion wie `make next-semester`.
   - Die Anmeldung für Schüler wird dabei automatisch geschlossen.
2. **AG-Registrierung öffnen**, damit AG-Leiter über „AG vorschlagen“ neue AGs einreichen können.

## Phase 2: AGs eingeben und prüfen

- Eingereichte AGs stehen im Tab **„AG Statistiken“** oben unter „Eingereicht, noch nicht genehmigt“.
- **Bearbeiten** (Stift-Symbol): Alle Angaben inkl. Termine und Status ändern. Mit Status „Genehmigt“ erscheint die AG bei der Anmeldung.
- **Duplizieren** (Kopieren-Symbol): Legt eine Kopie ohne Termine an (Status „Eingereicht“) und öffnet sie direkt zum Eintragen der neuen Termine. Praktisch, wenn dieselbe AG zu einem zweiten Termin angeboten wird.
- Mehrere AGs auf einmal genehmigen geht weiterhin im Django-Admin (Aktion „Ausgewählte AGs genehmigen“).
- Sind alle AGs geprüft: **AG-Registrierung schließen** und **Anmeldung für Schüler öffnen**.

## Phase 3: Anmeldung, Auslosung und Review

1. Eltern melden ihre Kinder an. Jedes Kind kann **höchstens 4 AGs** wählen, die Reihenfolge ist die Priorität (1 bis 4).
   Jede Anmeldung bekommt automatisch eine Eingangsbestätigung per E-Mail (noch keine Zusage).
2. **Anmeldung schließen.** Die Auslosung ist gesperrt, solange die Anmeldung offen ist.
3. **Auslosung starten.** Eine erneute Auslosung überschreibt alle bisherigen Zuteilungen.
4. **Vorläufige Listen an AG-Leiter:** Jede AG-Leitung bekommt ihre AG-Daten und die vorläufige Teilnehmer- und Warteliste
   zur Prüfung (ohne PDFs). Korrekturen kommen per Antwort-Mail zurück. Der Zähler zeigt, wie viele Listen verschickt sind;
   im AG-Tab steht pro AG „Vorläufig: Gesendet/Offen“ mit Einzel-Nachversand.
   Eine neue Auslosung setzt diesen Status zurück.
5. **Manuelle Korrektur:** Korrekturen der AG-Leiter und Sonderfälle eintragen (Status umschalten, Priorität ändern).
   Änderungen an AG-Daten (z.B. Ort, Termine) über „Bearbeiten“ im AG-Tab.

## Phase 4: E-Mail-Versand

1. **Mail an AG-Leiter:** Finale Teilnehmer- und Warteliste mit Abrechnungsvordruck und Listen als PDF.
2. **Mail an Teilnehmer:** Zusage mit allen zugeteilten AGs an die Eltern.

Beide Buttons verschicken nur Mails, die noch nicht erfolgreich versendet wurden. Ein zweiter Klick ist also gefahrlos
und holt fehlgeschlagene Mails nach. Einzelne Mails lassen sich im AG-Tab bzw. in der manuellen Korrektur erneut senden.

## Wie der E-Mail-Versand funktioniert

- Alle Mails werden **im Hintergrund** verschickt (Worker-Container `worker`). Nach dem Klick erscheint sofort
  „Der E-Mail-Versand läuft im Hintergrund“; der Gesendet-Status aktualisiert sich nach einem Neuladen der Seite.
- Bei vorübergehenden Fehlern (Timeout, Verbindungsabbruch, Mailserver meldet 4xx) wird bis zu 3-mal neu versucht.
  Dauerhafte Fehler (z.B. ungültige Adresse) bleiben als „nicht gesendet“ stehen und stehen in den Logs.
- Fehlgeschlagene Hintergrund-Aufgaben sind im Django-Admin unter „Tasks Database Backend“ einsehbar.
- **Termin-Erinnerungen:** Zwei Tage vor jedem AG-Termin bekommen alle zugelassenen Teilnehmer automatisch eine Erinnerung
  (nicht vor 8 Uhr, jede nur einmal). Versendete Erinnerungen stehen im Django-Admin unter „Termin-Erinnerungen“.
  Auf Staging ist der automatische Versand ausgeschaltet.
- **Test-E-Mail** im Tab „Allgemeine Statistiken & Funktionen“ prüft, ob der Mailversand grundsätzlich funktioniert.
