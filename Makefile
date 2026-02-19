.PHONY: up down reset-hard reset-soft test logs

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
