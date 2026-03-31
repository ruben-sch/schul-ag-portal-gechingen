.PHONY: up down reset-hard reset-soft test logs download-db restore-db

# Starten der Docker-Umgebung
up:
	docker compose up --build -d --remove-orphans

# Stoppen der Umgebung
down:
	docker compose down

# Radikaler Reset: Alle Container stoppen, Volumes (DB) löschen und neu starten
reset-hard:
	docker compose down -v
	docker compose up --build -d
	@echo "Warte auf Datenbank-Bereitschaft..."
	@sleep 5
	@echo "Radikaler Reset abgeschlossen. Admin (admin/admin123) wurde neu erstellt."

# Schneller Reset: Löscht nur Testdaten (AGs, Schüler, Anmeldungen) ohne Neustart
reset-soft:
	docker compose run --rm web python manage.py shell -c "from django.contrib.auth.models import User; from ags.models import AG, Anmeldung; Anmeldung.objects.all().delete(); AG.objects.all().delete(); User.objects.filter(is_superuser=False).delete(); print('Testdaten gelöscht (Admin behalten).')"

# Archiviert das aktuelle Halbjahr und bereitet die nächste Runde vor
next-semester:
	docker compose run --rm web python manage.py next_semester

# Simuliert 10 AGs und 100 Schüler über das UI
test:
	docker compose exec web python simulate_ui.py

# Zeigt die aktuellen Logs an
logs:
	docker compose logs -f

# Lädt einen Datenbank-Dump vom Produktionsserver herunter
download-db:
	@echo "Erstelle Dump auf dem Produktionsserver..."
	ssh root@135.181.30.178 "cd ~/schul-ag-portal && docker compose -f docker-compose.prod.yml exec -T db pg_dump -U ag_user -Fc ag_portal > prod_dump.dump"
	@echo "Kopiere Dump auf den lokalen Rechner..."
	scp root@135.181.30.178:~/schul-ag-portal/prod_dump.dump ./prod_dump.dump
	@echo "Datenbank-Dump erfolgreich heruntergeladen: prod_dump.dump"

# Spielt den heruntergeladenen Dump in die lokale Umgebung ein
restore-db:
	@if [ ! -f ./prod_dump.dump ]; then echo "Fehler: prod_dump.dump nicht gefunden. Führe erst 'make download-db' aus."; exit 1; fi
	@echo "Stelle sicher, dass die Datenbank läuft..."
	docker compose up -d db
	@echo "Warte kurz auf die Datenbank..."
	@sleep 3
	@echo "Spiele Dump ein (überschreibt existierende lokale Daten)..."
	docker compose exec -T db pg_restore -U ag_user -d ag_portal --clean --if-exists --no-owner < prod_dump.dump
	@echo "Starte Web-Container neu..."
	docker compose restart web
	@echo "Lokale Datenbank wurde aus prod_dump.dump wiederhergestellt!"
