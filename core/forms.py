from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import UserProfile


User = get_user_model()

INPUT_CLASS = "mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-cyan-400"


class CustomUserCreationForm(UserCreationForm):
    title = forms.ChoiceField(
        choices=UserProfile.TITLE_CHOICES,
        required=True,
        label="Title",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )

    full_name = forms.CharField(
        max_length=255,
        required=True,
        label="Full name",
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Your full name"}),
    )

    email = forms.EmailField(
        required=True,
        label="Email address",
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "you@example.com"}),
    )

    phone_number = forms.CharField(
        max_length=50,
        required=True,
        label="Phone number",
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "+44..."}),
    )

    level = forms.ChoiceField(
        choices=UserProfile.LEVEL_CHOICES,
        required=True,
        label="Profession",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "title",
            "full_name",
            "email",
            "phone_number",
            "level",
            "password1",
            "password2",
        )
        widgets = {
            "username": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Choose a username"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        user.is_active = False

        full_name = self.cleaned_data["full_name"].strip()
        name_parts = full_name.split(maxsplit=1)
        user.first_name = name_parts[0]
        if len(name_parts) > 1:
            user.last_name = name_parts[1]

        if commit:
            user.save()
            profile, _created = UserProfile.objects.get_or_create(user=user)
            profile.full_name = full_name
            profile.title = self.cleaned_data["title"]
            profile.phone_number = self.cleaned_data["phone_number"].strip()
            profile.level = self.cleaned_data["level"]
            profile.email_verified = False
            profile.save()

        return user


class ProfileUpdateForm(forms.Form):
    title = forms.ChoiceField(
        choices=UserProfile.TITLE_CHOICES,
        required=True,
        label="Title",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    full_name = forms.CharField(
        max_length=255,
        required=True,
        label="Full name",
        widget=forms.TextInput(attrs={"class": INPUT_CLASS}),
    )
    email = forms.EmailField(
        required=True,
        label="Email address",
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS}),
    )
    phone_number = forms.CharField(
        max_length=50,
        required=True,
        label="Phone number",
        widget=forms.TextInput(attrs={"class": INPUT_CLASS}),
    )
    level = forms.ChoiceField(
        choices=UserProfile.LEVEL_CHOICES,
        required=True,
        label="Profession",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )

    def __init__(self, *args, user=None, profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.profile = profile
        if profile and user and not self.is_bound:
            self.fields["title"].initial = profile.title
            self.fields["full_name"].initial = profile.full_name or user.get_full_name()
            self.fields["email"].initial = user.email
            self.fields["phone_number"].initial = profile.phone_number
            self.fields["level"].initial = profile.level

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError("Another account already uses this email.")
        return email

    def save(self):
        full_name = self.cleaned_data["full_name"].strip()
        name_parts = full_name.split(maxsplit=1)
        self.user.first_name = name_parts[0]
        self.user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        self.user.email = self.cleaned_data["email"].strip().lower()
        self.user.save(update_fields=["first_name", "last_name", "email"])

        self.profile.title = self.cleaned_data["title"]
        self.profile.full_name = full_name
        self.profile.phone_number = self.cleaned_data["phone_number"].strip()
        self.profile.level = self.cleaned_data["level"]
        self.profile.save(update_fields=["title", "full_name", "phone_number", "level"])
        return self.profile


class ResendVerificationForm(forms.Form):
    email = forms.EmailField(
        required=True,
        label="Email address",
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "you@example.com"}),
    )
