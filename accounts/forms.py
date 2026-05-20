from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password


User = get_user_model()


EMAIL_INPUT_ATTRS = {
    "placeholder": "Enter your email address",
    "autocomplete": "email",
}

NEW_PASSWORD_INPUT_ATTRS = {
    "placeholder": "Create a strong password",
    "autocomplete": "new-password",
}

CURRENT_PASSWORD_INPUT_ATTRS = {
    "placeholder": "Enter your password",
    "autocomplete": "current-password",
}


class RegisterForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs=EMAIL_INPUT_ATTRS),
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs=NEW_PASSWORD_INPUT_ATTRS),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                **NEW_PASSWORD_INPUT_ATTRS,
                "placeholder": "Confirm your password",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        email = User.objects.normalize_email(email).lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")

        return email

    def clean(self):
        cleaned_data = super().clean()

        email = cleaned_data.get("email")
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")

        if password1:
            temp_user = User(email=email)
            validate_password(password1, user=temp_user)

        return cleaned_data

    def save(self):
        return User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
        )


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs=EMAIL_INPUT_ATTRS),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs=CURRENT_PASSWORD_INPUT_ATTRS),
    )

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned_data = super().clean()

        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if not email or not password:
            return cleaned_data

        email = User.objects.normalize_email(email).lower()

        self.user = authenticate(
            self.request,
            username=email,
            password=password,
        )

        if self.user is None:
            raise forms.ValidationError("Invalid email or password.")

        if not self.user.is_active:
            raise forms.ValidationError("This account is inactive.")

        return cleaned_data

    def get_user(self):
        return self.user