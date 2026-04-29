# Diabbetes Prediction From
from django import forms

class DiabetesPredictionForm(forms.Form):
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female')]
    SMOKING_CHOICES = [
        (0, "Never"), (1, "No Info"), (2, "Current"), 
        (3, "Former"), (4, "Ever"), (5, "Not Current")
    ]
    YES_NO = [(1, "Yes"), (0, "No")]

    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    gender = forms.ChoiceField(choices=GENDER_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    age = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    hypertension = forms.ChoiceField(choices=YES_NO, widget=forms.Select(attrs={'class': 'form-select'}))
    heart_disease = forms.ChoiceField(choices=YES_NO, widget=forms.Select(attrs={'class': 'form-select'}))
    smoking_history = forms.ChoiceField(choices=SMOKING_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    bmi = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}))
    hba1c = forms.FloatField(label="HbA1c Level", widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}))
    glucose = forms.FloatField(label="Blood Glucose Level", widget=forms.NumberInput(attrs={'class': 'form-control'}))