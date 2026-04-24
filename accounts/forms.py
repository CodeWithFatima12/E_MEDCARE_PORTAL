from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password']
        
    def clean_username(self):
        username = self.cleaned_data['username']

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")

        return username
    
    def save(self, commit=True):
        user = super().save(commit=False)

        # email = username (as per your HTML)
        user.email = self.cleaned_data['username']
        user.username = self.cleaned_data['username']

        user.set_password(self.cleaned_data['password'])

        if commit:
            user.save()

        return user