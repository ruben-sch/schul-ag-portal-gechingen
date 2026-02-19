from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class AG(models.Model):
    STATUS_CHOICES = [
        ('SUBMITTED', 'Eingereicht'),
        ('APPROVED', 'Genehmigt'),
    ]

    name = models.CharField(max_length=200)
    beschreibung = models.TextField()
    kosten = models.DecimalField(max_digits=2, decimal_places=0, default=0)
    klassenstufe_min = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(4)])
    klassenstufe_max = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(4)])
    kapazitaet = models.PositiveIntegerField()
    termine = models.JSONField(default=list, help_text="Liste von Terminen mit Datum, Start- und Endzeit")
    ort = models.CharField(max_length=200, blank=True, help_text="Ort der AG, z.B. Turnhalle, Klassenzimmer 101")
    
    def get_termine_display(self):
        if not self.termine:
            return "Keine Termine"
        if isinstance(self.termine, str):
            return self.termine
        formatted = []
        for t in self.termine:
            datum = t.get('datum', '')
            try:
                # If it's an ISO date string, we can try to format it a bit nicer
                # but for simplicity we keep it as is or do a basic replacement
                if '-' in datum and len(datum) == 10:
                    y, m, d = datum.split('-')
                    datum = f"{d}.{m}.{y}"
            except:
                pass
            formatted.append(f"{datum} ({t.get('start', '')}-{t.get('ende', '')})")
        return ", ".join(formatted)
    mitzubringen = models.TextField(blank=True, help_text="Was müssen die Kinder mitbringen? (z.B. Sportzeug, Mäppchen)")
    hinweise = models.TextField(blank=True, help_text="Fragen / Organisatorische Hinweise")
    
    verantwortlicher_name = models.CharField(max_length=200)
    verantwortlicher_email = models.EmailField()
    verantwortlicher_telefon = models.CharField(max_length=50, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "AG"
        verbose_name_plural = "AGs"

class SchuelerProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='schueler_profiles')
    name = models.CharField(max_length=200, verbose_name="Name des Kindes", default="")
    klassenstufe = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(4)])
    notfall_telefon = models.CharField(max_length=50, verbose_name="Notfall-Telefonnummer", default='')

    class Meta:
        verbose_name = "Schüler"
        verbose_name_plural = "Schüler"

    def __str__(self):
        return f"{self.name} (Klasse {self.klassenstufe})"

class Anmeldung(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Wartend'),
        ('ACCEPTED', 'Zugelassen'),
        ('REJECTED', 'Abgelehnt/Warteliste'),
    ]

    schueler = models.ForeignKey(SchuelerProfile, on_delete=models.CASCADE, related_name='anmeldungen')
    ag = models.ForeignKey(AG, on_delete=models.CASCADE, related_name='anmeldungen')
    prio = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    erstellt_am = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        profile = self.schueler
        if profile:
            if self.ag.klassenstufe_min > profile.klassenstufe or self.ag.klassenstufe_max < profile.klassenstufe:
                raise ValidationError(f"Schüler in Klasse {profile.klassenstufe} darf nicht in AG '{self.ag.name}' (Klasse {self.ag.klassenstufe_min}-{self.ag.klassenstufe_max}).")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Anmeldung"
        verbose_name_plural = "Anmeldungen"

class ArchivEintrag(models.Model):
    schueler_name = models.CharField(max_length=200)
    schueler_email = models.EmailField()
    ag_name = models.CharField(max_length=200)
    halbyahr = models.CharField(max_length=20, help_text="z.B. 2023/24_H1")
    status = models.CharField(max_length=20)
    datum = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Archiv-Eintrag"
        verbose_name_plural = "Archiv-Einträge"
        ordering = ['-datum', 'schueler_name']

    def __str__(self):
        return f"{self.halbyahr}: {self.schueler_name} - {self.ag_name} ({self.status})"

class AppConfig(models.Model):
    anmeldung_offen = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Konfiguration"
        verbose_name_plural = "Konfigurationen"

    def __str__(self):
        return "Globale Einstellungen"
