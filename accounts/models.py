from django.conf import settings
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=160, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "companies"

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
