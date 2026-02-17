import random
from django.db import transaction
from django.contrib.auth.models import User
from django.db.models import Max, Count
from .models import AG, Anmeldung, SchuelerProfile

def reset_lottery():
    """Sets all registrations back to PENDING."""
    Anmeldung.objects.all().update(status='PENDING')

def run_lottery():
    with transaction.atomic():
        # 1. Reset
        Anmeldung.objects.all().update(status='REJECTED')
        
        # 2. Setup
        approved_ags = {ag.id: ag for ag in AG.objects.filter(status='APPROVED')}
        current_counts = {ag_id: 0 for ag_id in approved_ags.keys()}
        
        # Pre-fetch profiles and their class levels
        profiles = {p.id: p.klassenstufe for p in SchuelerProfile.objects.all()}

        # 3. Phase 1: JEDER Schueler (Profile) bekommt (wenn möglich) EINEN Platz
        all_profile_ids = list(Anmeldung.objects.values_list('schueler_id', flat=True).distinct())
        random.shuffle(all_profile_ids)
        
        for p_id in all_profile_ids:
            s_klasse = profiles.get(p_id)
            if s_klasse is None: continue
            
            wishes = Anmeldung.objects.filter(schueler_id=p_id, ag__status='APPROVED').order_by('prio')
            for wish in wishes:
                ag = approved_ags[wish.ag_id]
                if ag.klassenstufe_min <= s_klasse <= ag.klassenstufe_max:
                    if current_counts[ag.id] < ag.kapazitaet:
                        wish.status = 'ACCEPTED'
                        wish.save()
                        current_counts[ag.id] += 1
                        break
        
        # 4. Phase 2: Restliche Plätze so fair wie möglich auffüllen
        allocated_any = False
        while True:
            allocated_any = False
            
            # Recalculate how many AGs each student has
            accepted_counts = {
                row['schueler_id']: row['total'] 
                for row in Anmeldung.objects.filter(status='ACCEPTED')
                                     .values('schueler_id')
                                     .annotate(total=Count('id'))
            }
            
            # Find all rejected wishes where the AG still has space
            potential_wishes = []
            for wish in Anmeldung.objects.filter(status='REJECTED', ag__status='APPROVED').order_by('prio'):
                ag = approved_ags.get(wish.ag_id)
                if not ag: continue
                s_klasse = profiles.get(wish.schueler_id)
                if s_klasse is not None and ag.klassenstufe_min <= s_klasse <= ag.klassenstufe_max:
                    if current_counts[ag.id] < ag.kapazitaet:
                        potential_wishes.append(wish)
            
            if not potential_wishes:
                break
                
            # Sort potential wishes by the current occupancy of the student (fairness)
            potential_wishes.sort(key=lambda w: accepted_counts.get(w.schueler_id, 0))
            
            # Take the best candidate
            best_wish = potential_wishes[0]
            best_wish.status = 'ACCEPTED'
            best_wish.save()
            current_counts[best_wish.ag_id] += 1
            allocated_any = True
            
            if not allocated_any:
                break

        print("Zuteilung abgeschlossen.")
