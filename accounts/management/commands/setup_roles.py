from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from accounts.choices import SYSTEM_ROLES


class Command(BaseCommand):
    help = "Create the default TalentFlow user groups."

    def handle(self, *args, **options):
        for role in SYSTEM_ROLES:
            group, created = Group.objects.get_or_create(name=role)
            action = "Created" if created else "Found"
            self.stdout.write(self.style.SUCCESS(f"{action} group: {group.name}"))
