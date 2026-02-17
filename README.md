# AG-Verwaltungsportal Schlehengäuschule Gechingen

Dieses Portal dient der effizienten Verwaltung, Anmeldung und automatisierten Zuteilung von Arbeitsgemeinschaften (AGs). Es bietet Schnittstellen für AG-Leiter, Eltern/Schüler und Administratoren.

## 🚀 Hauptfunktionen

### 1. AG-Vorschläge & Verwaltung
- **AG einreichen:** Externe Leiter oder Lehrer können über ein Formular (`/propose/`) neue AG-Angebote einreichen.
- **Admin-Prüfung:** Administratoren prüfen eingereichte AGs im Django-Admin-Bereich, legen Kapazitäten fest und geben diese für die Anmeldung frei.

### 2. Schüler-Anmeldung (Zweistufig)
- **Schritt 1:** Eingabe der Stammdaten (Name, E-Mail, Klassenstufe 1-4, Notfall-Telefonnummer).
- **Schritt 2:** Auswahl der gewünschten AGs aus einer Liste, die automatisch nach der Klassenstufe des Kindes gefiltert wird.
- **Geschwister-Support:** Mehrere Kinder können über dieselbe E-Mail-Adresse angemeldet werden. Jedes Kind erhält ein eigenes Profil.

### 3. Automatisiertes Losverfahren (Lotterie)
Ein intelligenter Algorithmus teilt die Plätze in zwei Phasen zu:
- **Phase 1 (Fairness):** Jeder Schüler erhält (sofern Plätze frei sind) mindestens einen Platz in einer seiner gewählten AGs.
- **Phase 2 (Maximierung):** Verbleibende freie Plätze werden unter Berücksichtigung der Prioritäten aufgefüllt.
- Die Auslosung kann jederzeit im Statistik-Dashboard gestartet oder im Admin-Bereich zurückgesetzt ("Undo") werden.

### 4. Dashboards & Magic Links
Das System nutzt **Magic Links** (keine Passwörter nötig!):
- **Eltern-Dashboard:** Übersicht über alle Anmeldungen der Kinder einer Familie inklusive Status (Zugelassen / Warteliste).
- **Leiter-Dashboard:** AG-Leiter sehen eine vertikale, übersichtliche Liste ihrer Teilnehmer sowie eine vollständige Warteliste.
    - Exportierte Daten pro Teilnehmer: Name, Klasse, E-Mail und **Notfall-Telefonnummer**.

### 5. Semesterwechsel & Archivierung
Am Ende eines Halbjahres kann das System für die neue Runde vorbereitet werden:
- **Datenbank-Archiv:** Ergebnisse werden in der Tabelle **"Archiv-Einträge"** dauerhaft in der Datenbank gespeichert (Halbjahr, Schülername, AG, Status). Diese sind über das Admin-Interface jederzeit einsehbar.
- **JSON-Backup:** Zusätzlich wird eine Sicherungsdatei erstellt (`archives/`) und der Inhalt in die Logs ausgegeben (relevant für Cloud-Umgebungen).
- **Reset:** AGs, Anmeldungen und Benutzer (Schüler/Leiter) werden gelöscht, um Platz für die neue Runde zu machen.

---

## 🛠 Technische Bedienung (Entwickler/Admin)

Das System basiert auf **Django** und wird über **Docker** betrieben.

### Makefile Befehle
| Befehl | Beschreibung |
| :--- | :--- |
| `make up` | Startet die gesamte Umgebung (Docker) |
| `make down` | Stoppt alle Container |
| `make reset-hard` | Löscht die gesamte Datenbank und baut alles neu auf |
| `make test` | Startet eine automatisierte UI-Simulation (10 AGs, 100 Schüler) |
| `make next-semester` | Archiviert das Halbjahr und setzt das System zurück |
| `make logs` | Zeigt die Server-Logs in Echtzeit |

### Logins & Links
- **Admin-Bereich:** `http://localhost:8000/admin/` (Login: `admin` / `admin123`)
- **Statistik-Dashboard:** `http://localhost:8000/stats/` (Nur für Admins)
- **AG einreichen:** `http://localhost:8000/propose/`
- **Schüler-Anmeldung:** `http://localhost:8000/register/`

---

---

## ☁️ Hosting auf Google Cloud Run

Die App ist für das Hosting auf **Google Cloud Run** vorbereitet.

### Voraussetzungen
1. Ein Google Cloud Projekt mit aktivierter Abrechnung.
2. Installiertes `gcloud` CLI.
   - Projekt lokal setzen: `gcloud config set project schul-ag-portal-gechingen`
3. Eine **Cloud SQL (PostgreSQL)** Instanz.
   
   Du kannst eine Instanz mit folgendem Befehl erstellen (Region Frankfurt, kostengünstige Konfiguration):
   ```bash
   # 1. Instanz erstellen (kostengünstigste 'db-f1-micro')
   gcloud sql instances create schul-ag-db \
       --project=schul-ag-portal-gechingen \
       --database-version=POSTGRES_15 \
       --tier=db-f1-micro \
       --region=europe-west3 \
       --storage-type=HDD

   # 2. Datenbank innerhalb der Instanz erstellen
   gcloud sql databases create ag_portal --instance=schul-ag-db --project=schul-ag-portal-gechingen

   # 3. Datenbank-Benutzer erstellen
   gcloud sql users create ag_user --instance=schul-ag-db --password=DEIN_PASSWORT --project=schul-ag-portal-gechingen
   ```

### Deployment
Um die App zu deployen, führen Sie das bereitgestellte Skript aus:
```bash
./deploy_gcp.sh
```

Das Skript nutzt **Google Cloud Build**, um das Image zu erstellen und direkt in **Cloud Run** (Region Frankfurt) zu veröffentlichen. Statische Dateien werden via **WhiteNoise** automatisch serviert.

### Wichtige Umgebungsvariablen in der Cloud:
- `DATABASE_URL`: Verbindung zur Cloud SQL Instanz.
- `SECRET_KEY`: Ein sicherer Produktions-Key. 
  *(Generieren mit: `python3 -c 'import secrets; print(secrets.token_urlsafe(50))'`) *
- `DEBUG`: Muss in der Cloud `False` sein.

#### Format der `DATABASE_URL` für Cloud Run:
`postgres://BENUTZER:PASSWORT@/DATENBANK?host=/cloudsql/PROJEKT_ID:REGION:INSTANZ_NAME`

**Beispiel:**
`postgres://ag_user:geheim@/ag_portal?host=/cloudsql/mein-projekt-123:europe-west3:schul-ag-db`

#### So setzt du die Variablen:
1. **Google Cloud Console:** Navigiere zu Cloud Run -> Dienst auswählen -> "Neue Revision bearbeiten" -> Tab "Variablen & Geheimnisse".
2. **CLI (gcloud):** Sobald installiert, nutze `gcloud run services update schul-ag-portal --project=schul-ag-portal-gechingen --set-env-vars="KEY=VALUE,..."`

#### 🛡️ Best Practice: Secret Manager
Für sensible Daten (`DATABASE_URL`, `SECRET_KEY`) empfiehlt sich der **Google Cloud Secret Manager**:
1. Erstelle ein Secret im [Secret Manager](https://console.cloud.google.com/security/secret-manager).
2. Gewähre dem Cloud Run Service Account (meist `PROJECT_NUMBER-compute@developer.gserviceaccount.com`) die Rolle **"Secret Manager-Accessor"**.
3. Binde das Secret in Cloud Run als Umgebungsvariable ein: "Neue Revision bearbeiten" -> "Variablen & Geheimnisse" -> "Referenz auf ein Secret hinzufügen".
---

## 🚀 CI/CD & GitHub Actions

Das Projekt verfügt über vollautomatisierte Workflows (`.github/workflows/`):

1.  **Tests & Linting (`test.yml`)**: Läuft bei jedem Push/Pull Request. Führt Unittests, Flake8 (Syntax) und Bandit (Sicherheit) aus.
2.  **Deployment (`deploy.yml`)**: Deployed die App automatisch auf Google Cloud Run, wenn auf `main` gepusht wird.
3.  **CodeQL (`codeql.yml`)**: Erweitere Sicherheitsanalyse durch GitHub.
4.  **Dependabot**: Prüft wöchentlich auf veraltete Abhängigkeiten.

### Notwendige GitHub Secrets
Damit das Deployment funktioniert, müssen im GitHub Repository unter `Settings -> Secrets and variables -> Actions` folgende Secrets hinterlegt werden:

| Secret Name | Wert |
| :--- | :--- |
| `GCP_PROJECT_ID` | Die ID Ihres Google Cloud Projekts |
| `GCP_SA_KEY` | Der JSON-Key eines Service Accounts mit Cloud Run Admin & Storage Admin Rechten |
