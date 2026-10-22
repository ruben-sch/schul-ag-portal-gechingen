# Admin-Handbuch: Ablauf eines Halbjahres

Dieses Handbuch beschreibt, wie ein Halbjahr im AG-Portal von der AG-Eingabe bis zum Versand der Zusagen läuft.
Alle Schritte findest du im Admin-Bereich unter **Statistik & Losverfahren → Tab „Workflow“** (`/stats/`).
Der Tab ist in vier Phasen gegliedert, die du von oben nach unten abarbeitest.

## Phase 1: Neues Halbjahr starten

1. **Neues Halbjahr starten:** `NEUES HALBJAHR` in das Feld tippen und den Button drücken.
   - Alle Anmeldungen der laufenden Runde werden ins Archiv übernommen (Django-Admin → „Archiv-Einträge“).
   - Danach werden **alle AGs, Schüler, Anmeldungen sowie die Konten von Eltern und AG-Leitern gelöscht**.
     Admin- und Staff-Konten bleiben erhalten; Leiter-Konten entstehen beim nächsten Einreichen oder Bearbeiten einer AG neu.
   - Zusätzlich wird auf dem Server eine JSON-Sicherung abgelegt (nicht in den Logs). Das ist dieselbe Funktion wie `make next-semester`.
   - Der Wechsel läuft komplett oder gar nicht; ein Doppelklick archiviert nichts doppelt.
   - Die Anmeldung für Schüler wird automatisch geschlossen und die **AG-Registrierung geöffnet**, damit AG-Leiter
     über „AG vorschlagen“ direkt neue AGs einreichen können.

## Phase 2: AGs eingeben und prüfen

- Eingereichte AGs stehen im Tab **„AG Statistiken“** oben unter „Eingereicht, noch nicht genehmigt“.
- **Bearbeiten** (Stift-Symbol): Alle Angaben inkl. Termine und Status ändern. Mit Status „Genehmigt“ erscheint die AG bei der Anmeldung.
- **Duplizieren** (Kopieren-Symbol): Legt eine Kopie ohne Termine an (Status „Eingereicht“) und öffnet sie direkt zum Eintragen der neuen Termine. Praktisch, wenn dieselbe AG zu einem zweiten Termin angeboten wird.
- Mehrere AGs auf einmal genehmigen geht weiterhin im Django-Admin (Aktion „Ausgewählte AGs genehmigen“).
  Auslosen, Zurücksetzen, Mailversand und Halbjahreswechsel gibt es nur im Workflow-Tab, damit dessen Sperren immer gelten.
- Sind alle AGs geprüft: **AG-Registrierung schließen** (Schalter in Phase 1) und **Anmeldung für Schüler öffnen** (Schalter in Phase 3).

## Phase 3: Anmeldung, Auslosung und Review

1. Eltern melden ihre Kinder an. Jedes Kind kann **höchstens 4 AGs** wählen, die Reihenfolge ist die Priorität (1 bis 4). Das laufende Halbjahr bleibt noch bei 5 AGs; der Halbjahreswechsel stellt auf 4 um.
   Jede Anmeldung bekommt automatisch eine Eingangsbestätigung per E-Mail (noch keine Zusage).
2. **Anmeldung schließen.** Die Auslosung ist gesperrt, solange die Anmeldung offen ist.
3. **Auslosung starten.** Eine erneute Auslosung überschreibt alle bisherigen Zuteilungen. Sobald die endgültigen Mails
   aus Phase 4 verschickt sind, ist die Auslosung gesperrt; danach nur noch über die manuelle Korrektur ändern.
   **Auslosung zurücksetzen** stellt alle Anmeldungen wieder auf „Wartend“ (z.B. wenn die Anmeldung noch einmal
   geöffnet werden soll). Es gilt dieselbe Sperre: nicht bei offener Anmeldung und nicht nach den endgültigen Mails.
4. **Vorläufige Listen an AG-Leiter:** Jede AG-Leitung bekommt ihre AG-Daten und die vorläufige Teilnehmer- und Warteliste
   zur Prüfung (ohne PDFs). Das geht erst nach der Auslosung und nicht mehr für AGs, deren endgültige Liste schon
   verschickt ist. Korrekturen kommen per Antwort-Mail zurück. Der Zähler zeigt, wie viele Listen verschickt sind;
   im AG-Tab steht pro AG „Vorläufig: Gesendet/Offen“ mit Einzel-Nachversand.
   Eine neue Auslosung setzt diesen Status zurück.
5. **Manuelle Korrektur:** Korrekturen der AG-Leiter und Sonderfälle eintragen (Status umschalten, Priorität ändern).
   Änderungen an AG-Daten (z.B. Ort, Termine) über „Bearbeiten“ im AG-Tab.

## Phase 4: E-Mail-Versand

1. **Mail an AG-Leiter:** Finale Teilnehmer- und Warteliste mit Abrechnungsvordruck und Listen als PDF.
2. **Mail an Teilnehmer:** Zusage mit allen zugeteilten AGs an die Eltern.
   Eltern, deren Kind **keinen Platz** bekommen hat (nur Warteliste), bekommen **keine Mail**. Das muss die Schule
   bei Bedarf selbst mitteilen.

Beide Buttons verschicken nur Mails, die noch nicht erfolgreich versendet wurden. Ein zweiter Klick ist also gefahrlos
und holt fehlgeschlagene Mails nach.

**Korrekturen nach dem Versand** (manuelle Korrektur) setzen den Gesendet-Status nicht zurück. Die Buttons schicken
deshalb nichts an bereits Benachrichtigte. Betroffene Eltern bzw. AG-Leitungen bitte einzeln neu anschreiben: in der
manuellen Korrektur (Senden-Symbol bei „Zuteilung“) bzw. im AG-Tab (Senden-Symbol bei „Final“).

## Wie der E-Mail-Versand funktioniert

- Alle Mails werden **im Hintergrund** verschickt (Worker-Container `worker`). Nach dem Klick erscheint sofort
  „Der E-Mail-Versand läuft im Hintergrund“; der Gesendet-Status aktualisiert sich nach einem Neuladen der Seite.
- Massenversände laufen in Paketen zu 10 Mails. Eingangsbestätigungen für neue Anmeldungen werden dazwischen vorgezogen.
- Eine Mail wird insgesamt bis zu 3-mal versucht (2 Wiederholungen nach 5 bzw. 10 s), aber nur, wenn sie sicher nicht
  angekommen ist: beim Verbindungsaufbau oder wenn der Mailserver sie vorübergehend ablehnt (4xx). Ein Abbruch mitten im
  Senden wird nicht wiederholt, damit keine Mail doppelt ankommt.
  Dauerhafte Fehler (z.B. ungültige Adresse) bleiben als „nicht gesendet“ stehen.
- Nicht versendete Mails erkennst du am Status „Fehlt“ im AG-Tab bzw. in der manuellen Korrektur. Zusätzlich steht die
  zugehörige Hintergrund-Aufgabe im Django-Admin unter „Tasks Database Backend“ als fehlgeschlagen, mit der Zahl der
  betroffenen Mails; Details stehen in den Worker-Logs.
- **Termin-Erinnerungen:** Für jeden AG-Termin in den nächsten zwei Tagen bekommen die zugeteilten Teilnehmer automatisch
  eine Erinnerung, also bis zu zwei Tage vorher; wer verpasst wurde, wird noch am Vortag erinnert (nicht vor 8 Uhr, jede
  nur einmal). Erinnert wird erst, wenn die Familie die Zusage-Mail aus Phase 4 bekommen hat.
  Versendete und dauerhaft fehlgeschlagene Erinnerungen stehen im Django-Admin unter „Termin-Erinnerungen“.
  Auf Staging ist der automatische Versand ausgeschaltet.
- **Test-E-Mail** im Tab „Allgemeine Statistiken & Funktionen“ prüft, ob der Mailversand grundsätzlich funktioniert.
