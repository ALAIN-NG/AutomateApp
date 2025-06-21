from django import forms
from .models import Automate, Etat, Transition


class AutomateForm(forms.ModelForm):
    class Meta:
        model = Automate
        fields = ['nom', 'type', 'alphabet']


class EtatForm(forms.ModelForm):
    class Meta:
        model = Etat
        fields = ['nom', 'est_initial', 'est_final']



class TransitionForm(forms.ModelForm):
    class Meta:
        model = Transition
        fields = ['source', 'symbole', 'cible']

    def __init__(self, *args, automate=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.automate = automate

        if automate:
            self.fields['source'].queryset = automate.etats.all()
            self.fields['cible'].queryset = automate.etats.all()

            # 🎯 Construire la liste des symboles de l'automate
            alphabet = [s.strip() for s in automate.alphabet.split(',')]
            self.fields['symbole'] = forms.ChoiceField(
                choices=[(s, s) for s in alphabet],
                label="Symbole"
            )

    def clean(self):
        cleaned_data = super().clean()
        source = cleaned_data.get("source")
        symbole = cleaned_data.get("symbole")

        if self.automate and self.automate.type == 'DFA' and source and symbole:
            conflit = Transition.objects.filter(
                automate=self.automate,
                source=source,
                symbole=symbole
            )
            if self.instance.pk:
                conflit = conflit.exclude(pk=self.instance.pk)

            if conflit.exists():
                raise forms.ValidationError(
                    f"❌ Conflit : une transition existe déjà de {source} avec '{symbole}' dans un AFD."
                )
        return cleaned_data



class ExpressionReguliereForm(forms.Form):
    expression = forms.CharField(
        label="Expression régulière",
        max_length=255,
        widget=forms.TextInput(attrs={
            'placeholder': 'ex: (a+b)*abb',
            'class': 'w-full border px-4 py-2 rounded'
        })
    )
    
    ALGORITHMES = [
        ('thompson', 'Thompson pur'),
        ('glushkov', 'Glushkov'),
    ]

    algorithme = forms.ChoiceField(
        label="Algorithme de génération",
        choices=ALGORITHMES,
        widget=forms.RadioSelect
    )







class EquationForm(forms.Form):
    systeme = forms.CharField(
        label="Système d'équations",
        widget=forms.Textarea(attrs={
            'rows': 7,
            'placeholder': "Ex :\nX0 = bX0 + aX1\nX1 = aX2 + bX3\nX2 = aX1\nX3 = ε"
        })
    )
