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

## 🌐 Hosting auf Hetzner VPS

Das Projekt ist für das Deployment auf einem Linux-Server (z.B. Hetzner VPS) vorbereitet. Die Auslieferung erfolgt via **Docker Compose** und **GitHub Actions**.

### Voraussetzungen auf dem Server
1. **Docker & Docker Compose** müssen installiert sein.
2. Ein Ordner `~/schul-ag-portal/` sollte existieren.
3. SSH-Zugriff via SSH-Key muss möglich sein.
   
#### 🔑 SSH-Key für Hetzner erstellen
Um einen sicheren SSH-Key speziell für GitHub Actions zu erstellen, führe lokal folgende Befehle aus:

```bash
# 1. Key generieren (ohne Passwort für CI/CD)
ssh-keygen -t ed25519 -C "github-actions-deployment" -f ./id_ed25519_hetzner -N ""

# 2. Public Key auf den Server kopieren (ersetze IP und User)
ssh-copy-id -i ./id_ed25519_hetzner.pub root@123.123.123.123
```

- Den Inhalt von `id_ed25519_hetzner` (privater Key) kopierst du in das GitHub Secret `HETZNER_SSH_KEY`.
- Danach kannst du die Dateien `id_ed25519_hetzner` und `id_ed25519_hetzner.pub` lokal wieder löschen.

### Automatisches Deployment
Sobald Änderungen in den `main` Branch gepusht werden, baut GitHub ein Image, lädt es in die **GitHub Container Registry (GHCR)** hoch und startet die Container auf dem Hetzner-Server neu.

### E-Mail Versand mit Resend (Produktion)

Für den E-Mail-Versand in der Produktion wird **Resend** empfohlen.

1.  **Account erstellen**: Registriere dich bei [Resend.com](https://resend.com/).
2.  **Domain verifizieren**: Füge deine Domain (z.B. `schwarzpost.de`) hinzu und hinterlege die angezeigten DNS-Einträge (SPF/DKIM) bei deinem Domain-Provider.
3.  **API-Key erstellen**: Erstelle einen API-Key mit "Sending" Berechtigung.

### Notwendige GitHub Secrets

Damit das Deployment und der E-Mail-Versand funktionieren, müssen im GitHub Repository folgende Secrets hinterlegt werden:

| Secret Name | Beschreibung |
| :--- | :--- |
| `HETZNER_HOST` | IP-Adresse oder Domain des Servers |
| `HETZNER_USER` | SSH-Benutzername (z.B. `root`) |
| `HETZNER_SSH_KEY` | Privater SSH-Key für den Zugriff |
| `SECRET_KEY` | Ein sicherer Django Secret Key |
| `POSTGRES_PASSWORD` | Passwort für die PostgreSQL Datenbank |
| `ALLOWED_HOSTS` | Kommagetrennte Liste der Domains, z.B. `schul-ag.schwarzpost.de,schul-ag.foerderverein-sgs-gechingen.de` |
| `CSRF_TRUSTED_ORIGINS` | Kommagetrennte Liste der vertrauenswürdigen Origins, z.B. `https://schul-ag.schwarzpost.de` |
| `SMTP_HOST` | Host für Resend: `smtp.resend.com` |
| `SMTP_USER` | Der Wert `resend` |
| `SMTP_PASSWORD` | Dein Resend API-Key (beginnt mit `re_...`) |
| `ACME_EMAIL` | E-Mail für Let's Encrypt Benachrichtigungen |

### Ersten Admin-Account erstellen
Da die Datenbank auf dem Server leer startet, musst du einmalig manuell einen Administrator anlegen. Führe dazu diesen Befehl auf deinem Hetzner-Server aus:

```bash
cd ~/schul-ag-portal/
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

Folge danach den Anweisungen im Terminal, um Benutzername, E-Mail und Passwort festzulegen.

---

## 🚀 CI/CD & GitHub Actions

Das Projekt verfügt über vollautomatisierte Workflows (`.github/workflows/`):

1.  **Tests & Linting (`test.yml`)**: Läuft bei jedem Push/Pull Request. Führt Unittests, Flake8 (Syntax) und Bandit (Sicherheit) aus.
2.  **Deployment (`deploy-hetzner.yml`)**: Deployed die App automatisch auf den Hetzner VPS:
    - **Staging Umgebung:** Ein Push auf `main` deployed automatisch eine Staging-Instanz (getrennte Container, eigene Sub-Subdomain `staging`). Diese ist durch **Traefik Basic Auth** geschützt (gleiche Zugangsdaten wie für das Traefik-Dashboard).
    - **Produktions Umgebung:** Ein Deployment für Produktion wird **ausschließlich** durch die Erstellung eines neuen GitHub Releases (Tags) ausgelöst.
3.  **CodeQL**: Erweitere Sicherheitsanalyse durch GitHub.
4.  **Dependabot**: Prüft wöchentlich auf veraltete Abhängigkeiten.
