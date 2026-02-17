import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from ags.models import AG, Anmeldung, SchuelerProfile
from django.db.models import Count

def diagnose():
    print("--- LOTTERY DIAGNOSIS ---")
    
    # 1. Check for empty slots in approved AGs
    ags = AG.objects.filter(status='APPROVED').annotate(
        accepted_count=Count('anmeldungen', filter=django.db.models.Q(anmeldungen__status='ACCEPTED')),
        rejected_count=Count('anmeldungen', filter=django.db.models.Q(anmeldungen__status='REJECTED'))
    )
    
    found_issue = False
    for ag in ags:
        free_slots = ag.kapazitaet - ag.accepted_count
        if free_slots > 0 and ag.rejected_count > 0:
            found_issue = True
            print(f"\nAG '{ag.name}' (ID: {ag.id}):")
            print(f"  - Kapazität: {ag.kapazitaet}")
            print(f"  - Zugelassen: {ag.accepted_count}")
            print(f"  - Freie Plätze: {free_slots}")
            print(f"  - Auf Warteliste: {ag.rejected_count} (!!!)")
            
            # Check why the first person on the waitlist wasn't picked
            sample_rejected = Anmeldung.objects.filter(ag=ag, status='REJECTED').first()
            if sample_rejected:
                student = sample_rejected.schueler
                profile = getattr(student, 'schueler_profile', None)
                print(f"  - Beispiel-Bewerber auf Warteliste: {student.email}")
                if profile:
                    print(f"    - Klassenstufe Schüler: {profile.klassenstufe}")
                    print(f"    - AG Bereich: {ag.klassenstufe_min} - {ag.klassenstufe_max}")
                    if profile.klassenstufe < ag.klassenstufe_min or profile.klassenstufe > ag.klassenstufe_max:
                        print("    -> URSACHE: Klassenstufe passt nicht!")
                    else:
                        print("    -> Klassenstufe PASST. Logikfehler im Algorithmus?")

    if not found_issue:
        print("\nKeine AGs gefunden, bei denen Plätze frei sind TROTZ Warteliste.")
        print("Mögliche Ursache in der Statistik-Anzeige?")

if __name__ == '__main__':
    diagnose()
