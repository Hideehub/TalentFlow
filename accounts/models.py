import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .choices import SYSTEM_ROLES

INVITATION_LIFETIME = timedelta(days=7)


def generate_invitation_token():
    return secrets.token_urlsafe(32)


def default_invitation_expiry():
    return timezone.now() + INVITATION_LIFETIME


class Company(models.Model):
    name = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "companies"
        constraints = (
            models.UniqueConstraint(Lower("name"), name="unique_company_name_ci"),
        )

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="members",
    )

    class Meta:
        ordering = ("user__username",)

    def __str__(self):
        return f"{self.user} - {self.company}"


class Invitation(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=30,
        choices=[(role, role) for role in SYSTEM_ROLES],
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_invitation_token,
        editable=False,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="sent_invitations",
        null=True,
    )
    expires_at = models.DateTimeField(default=default_invitation_expiry)
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.email} - {self.company}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self):
        return self.accepted_at is None and not self.is_expired
