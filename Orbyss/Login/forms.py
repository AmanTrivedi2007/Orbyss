from django import forms
from django.contrib.auth.models import User
import re

class RegisterForm(forms.Form):

    first_name=forms.CharField(max_length=100)

    last_name=forms.CharField(max_length=100)

    email=forms.EmailField()

    password=forms.CharField(
        widget=forms.PasswordInput
    )

    company=forms.CharField(
        required=False
    )


    def clean_email(self):

        email=self.cleaned_data["email"]

        if User.objects.filter(
            email=email
        ).exists():

            raise forms.ValidationError(
                "Email already exists"
            )

        return email


    def clean_password(self):

        password=self.cleaned_data["password"]

        if len(password)<8:

            raise forms.ValidationError(
                "Password must contain at least 8 characters"
            )

        if not re.search(
            "[A-Z]",
            password
        ):

            raise forms.ValidationError(
                "Password must contain at least one uppercase letter"
            )

        if not re.search(
            "[0-9]",
            password
        ):

            raise forms.ValidationError(
                "Password must contain at least one number"
            )

        if not re.search(
            "[!@#$%^&*(),.?\":{}|<>]",
            password
        ):

            raise forms.ValidationError(
                "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)"
            )

        return password