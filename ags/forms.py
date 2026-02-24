from django import forms
from .models import AG, SchuelerProfile

class AGProposalForm(forms.ModelForm):
    class Meta:
        model = AG
        fields = [
            'name', 'beschreibung', 'kosten', 
            'klassenstufe_min', 'klassenstufe_max', 
            'kapazitaet', 'ort', 'termine', 'mitzubringen', 'hinweise',
            'verantwortlicher_name', 'verantwortlicher_email', 'verantwortlicher_telefon'
        ]
        widgets = {
            'beschreibung': forms.Textarea(attrs={'rows': 4}),
            'termine': forms.HiddenInput(),
            'mitzubringen': forms.Textarea(attrs={'rows': 2, 'placeholder': 'z.B. Sportkleidung'}),
            'hinweise': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'verantwortlicher_name': 'Name',
            'verantwortlicher_email': 'E-Mail',
            'verantwortlicher_telefon': 'Telefon',
            'kosten': 'Kosten (in €)',
            'kapazitaet': 'Maximale Teilnehmerzahl',
            'klassenstufe_min': 'Klassenstufe (min)',
            'klassenstufe_max': 'Klassenstufe (max)',
            'ort': 'Ort / Räumlichkeit',
        }

class SchuelerFirstStepForm(forms.Form):
    name = forms.CharField(label="Vollständiger Name", max_length=200)
    email = forms.EmailField(label="E-Mail")
    klassenstufe = forms.IntegerField(label="Klassenstufe", min_value=1, max_value=4)
    notfall_telefon = forms.CharField(label="Notfall-Telefonnummer", max_length=50, help_text="Nummer, unter der Ihre Eltern erreichbar sind.")

class LoginForm(forms.Form):
    email = forms.EmailField(label="E-Mail-Adresse")
