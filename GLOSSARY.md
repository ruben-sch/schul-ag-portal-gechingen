# Glossar

Fachbegriffe des AG-Portals, wie sie im Code, in der UI und in Issues verwendet werden.

| Begriff | Bedeutung |
| --- | --- |
| **Halbjahr** | Eine Runde von der AG-Einreichung bis zum Versand der Zusagen. Endet mit dem Halbjahreswechsel (`halbjahr.neues_halbjahr`), der archiviert und alle AGs, Schüler und Anmeldungen löscht. |
| **Phase** | Der Stand eines Halbjahres. Wird nicht gespeichert, sondern aus `AppConfig`-Schaltern, Anmeldungsstatus und Versand-Flags abgeleitet (`halbjahr.phase()`). |
| **Auslosung** | Zuteilung der Anmeldungen auf AG-Plätze nach Priorität und Fairness (`utils.run_lottery`). Vorher sind alle Anmeldungen „Wartend“ (PENDING). |
| **Zurücksetzen** | Macht eine Auslosung rückgängig: alle Anmeldungen wieder „Wartend“. |
| **Vorläufige Liste** | Teilnehmer- und Warteliste, die die AG-Leitung nach der Auslosung zur Prüfung bekommt, ohne PDFs. |
| **Endgültige Mails** | Finale Liste an die AG-Leitung (`AG.leader_email_sent`) und Zusage an die Eltern (`SchuelerProfile.acceptance_email_sent`). Danach sind Auslosen und Zurücksetzen gesperrt. |
| **Sperrgrund** | Deutscher Satz, warum eine Aktion in der aktuellen Phase nicht erlaubt ist; leer heißt erlaubt. Steht als Tooltip am deaktivierten Button und als Fehlermeldung. |
