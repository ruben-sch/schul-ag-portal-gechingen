from django import forms
from .models import AG, SchuelerProfile

class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'termine':
                continue
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input bg-dark border-secondary'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select bg-dark text-light border-secondary focus-ring focus-ring-primary'
            else:
                field.widget.attrs['class'] = 'form-control bg-dark text-light border-secondary focus-ring focus-ring-primary'

class AGProposalForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AG
        fields = [
            'name', 'beschreibung', 'kosten', 
            'klassenstufe_min', 'klassenstufe_max', 
            'kapazitaet', 'termine', 'mitzubringen', 'hinweise',
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
        }

class SchuelerFirstStepForm(BootstrapFormMixin, forms.Form):
    name = forms.CharField(label="Vollständiger Name", max_length=200)
    email = forms.EmailField(label="E-Mail")
    klassenstufe = forms.IntegerField(label="Klassenstufe", min_value=1, max_value=4)
    notfall_telefon = forms.CharField(label="Notfall-Telefonnummer", max_length=50, help_text="Nummer, unter der Ihre Eltern erreichbar sind.")

class LoginForm(BootstrapFormMixin, forms.Form):
    email = forms.EmailField(label="E-Mail-Adresse")
