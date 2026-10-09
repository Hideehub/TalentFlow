from django.contrib import admin

from .models import Company, Invitation, UserProfile


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company")
    list_filter = ("company",)
    search_fields = ("user__username", "user__email", "company__name")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "company", "role", "invited_by", "expires_at", "accepted_at")
    list_filter = ("company", "role")
    search_fields = ("email", "company__name")
