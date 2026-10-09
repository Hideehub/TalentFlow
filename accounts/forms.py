from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from .models import Company, Invitation

COMPANY_NAME_TAKEN = "A company with this name already exists. Ask its HR Admin for an invite."


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))
    company_name = forms.CharField(
        label="Company",
        max_length=160,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email", "company_name")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": "form-control"})
        self.fields["password2"].widget.attrs.update({"class": "form-control"})

    def clean_company_name(self):
        company_name = self.cleaned_data["company_name"].strip()
        if Company.objects.filter(name__iexact=company_name).exists():
            raise forms.ValidationError(COMPANY_NAME_TAKEN)
        return company_name


class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ("email", "role")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(
            profile__company=self.company, email__iexact=email
        ).exists():
            raise forms.ValidationError("This person is already a member of your company.")
        if Invitation.objects.filter(
            company=self.company,
            email__iexact=email,
            accepted_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).exists():
            raise forms.ValidationError("This email already has a pending invite.")
        return email


class InvitationAcceptForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = get_user_model()
        fields = ("username", "first_name", "last_name")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": "form-control"})
        self.fields["password2"].widget.attrs.update({"class": "form-control"})
