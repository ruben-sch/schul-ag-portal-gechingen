# ADR 002: Konzept für Staging-Umgebung

## Status
APPROVED

## Context
Um neue Features vor dem Release auf einem Server realistisch testen zu können, ohne die Produktionsdaten zu gefährden, wird eine Staging-Umgebung benötigt (Issue #27). Diese Umgebung soll die Architektur der Produktionsumgebung exakt abbilden und automatisiert aus der Pipeline deployed werden.

## Decision
Wir führen eine mandantenfähige Architektur auf Instanzebene (Container) ein, um eine Staging-Umgebung neben der Produktion auf demselben Server zu betreiben.

### 1. Architektur und Isolation
*   **Traefik als zentraler Reverse Proxy**: Sowohl die Produktions- als auch die Staging-Umgebung werden hinter einer einzigen gemeinsamen Traefik-Instanz betrieben. Traefik routet die Requests anhand des Hostnamens dynamisch an den richtigen Container.
*   **Getrennte Container**: Es wird explizit getrennte `web`-Container (Django) und `db`-Container (PostgreSQL) geben. 
*   **Strikte Datentrennung**: Die Staging- und Produktions-Datenbanken bekommen voneinander separierte Docker-Volumes und getrennte Zugangsdaten. Ein netzwerktechnischer oder logischer Zugriff der Staging-Umgebung auf Produktionsdaten und umgekehrt ist somit komplett ausgeschlossen.
*   **Docker Compose**: Die Konfiguration wird mittels neuer Services in den bestehenden Compose-Dateien (`docker-compose.prod.yml`) realisiert.

### 2. URL und Routing
*   Es wird folgende Sub-Subdomain für die Umgebung festgelegt: **`staging.schul-ag.schwarzpost.de`**
*   Dies sorgt für eine logische Unterordnung unter das Hauptprojekt und ermöglicht die einfache Verwendung von Wildcard-Features oder klaren DNS-Strukturen in der Zukunft.

### 3. Zugriffsschutz (Security)
*   Die Staging-Umgebung darf nicht von der Öffentlichkeit oder Suchmaschinen erreicht werden.
*   Analog zum existierenden Traefik-Dashboard wird der Staging-Web-Container durch eine **Basic Authentication Middleware** in Traefik geschützt. Hierbei werden **dieselben Basic Auth Credentials** verwendet, die bereits für das Traefik-Dashboard konfiguriert sind. Ohne Benutzername und Passwort ist der Zugriff auf die Applikation blockiert.

### 4. CI/CD Deployment-Pipeline
Die Deployment-Strategie in GitHub Actions wird in zwei getrennte Trigger aufgeteilt, um Kontrolle zu gewährleisten:
*   **Staging Deployment**: Wird komplett automatisiert bei jedem **Merge auf den `main`-Branch** ausgelöst. So spiegelt Staging exakt den neuesten Code-Stand von main.
*   **Production Deployment**: Erfolgt ab sofort nicht mehr bei jedem Push auf `main`, sondern wird **nur noch bei der Erstellung eines neuen GitHub Releases (Tags)** angestoßen. 

## Consequences
*   Die `docker-compose.prod.yml` muss um die Staging-Services (`web-staging`, `db-staging`) und Traefik Basic Auth Labels ergänzt werden.
*   Der bestehende Workflow `.github/workflows/deploy-hetzner.yml` wird zweigeteilt (oder nutzt bedingte Jobs), um zwischen Staging-Push (Event `push to main`) und Prod-Release (Event `release`) zu unterscheiden.
*   Auf dem Server (bzw. in den GitHub Secrets) müssen neue Variablen angelegt werden, u.a. Basic Auth Credentials für Traefik und getrennte DB-Zugangsdaten für Staging.
