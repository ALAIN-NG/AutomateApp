# models.py
from django.db import models

class Automate(models.Model):
    TYPE_CHOICES = [
        ('DFA', 'Deterministe'),
        ('NFA', 'Non Deterministe'),
        ('EFA', 'Epsilon-transitions'),
    ]
    nom = models.CharField(max_length=100)
    type = models.CharField(max_length=3, choices=TYPE_CHOICES, default='DFA')
    alphabet = models.CharField(max_length=100, help_text="Ex: a,b,c")

    def __str__(self):
        return f"{self.nom} ({self.get_type_display()})"


class Etat(models.Model):
    automate = models.ForeignKey(Automate, on_delete=models.CASCADE, related_name='etats')
    nom = models.CharField(max_length=50)
    est_initial = models.BooleanField(default=False)
    est_final = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nom}{' (init)' if self.est_initial else ''}{' (final)' if self.est_final else ''}"


class Transition(models.Model):
    automate = models.ForeignKey(Automate, on_delete=models.CASCADE, related_name='transitions')
    source = models.ForeignKey(Etat, on_delete=models.CASCADE, related_name='transitions_sortantes')
    symbole = models.CharField(max_length=10, help_text="Ex: a, b, ou ε")
    cible = models.ForeignKey(Etat, on_delete=models.CASCADE, related_name='transitions_entrantes')

    def __str__(self):
        return f"{self.source.nom} --{self.symbole}--> {self.cible.nom}"
