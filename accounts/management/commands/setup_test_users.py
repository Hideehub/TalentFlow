from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from accounts.choices import (
    ROLE_HIRING_MANAGER,
    ROLE_HR_ADMIN,
    ROLE_RECRUITER,
    SYSTEM_ROLES,
)
from accounts.models import Company, UserProfile


DEFAULT_COMPANY = "TalentFlow Demo Company"


TEST_USERS = (
    {
        "username": "recruiter",
        "email": "recruiter@talentflow.test",
        "first_name": "Recruiter",
        "last_name": "User",
        "role": ROLE_RECRUITER,
    },
    {
        "username": "hiringmanager",
        "email": "hiring.manager@talentflow.test",
        "first_name": "Hiring",
        "last_name": "Manager",
        "role": ROLE_HIRING_MANAGER,
    },
    {
        "username": "hradmin",
        "email": "hr.admin@talentflow.test",
        "first_name": "HR",
        "last_name": "Admin",
        "role": ROLE_HR_ADMIN,
    },
)


class Command(BaseCommand):
    help = "Create TalentFlow role groups and one test user for each role."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="TalentFlow123!",
            help="Password to set for all test users.",
        )
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Reset passwords for existing test users.",
        )
        parser.add_argument(
            "--company",
            default=DEFAULT_COMPANY,
            help="Company name to attach the test users to.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        password = options["password"]
        reset_passwords = options["reset_passwords"]
        company, _created = Company.objects.get_or_create(name=options["company"])

        groups = {}
        for role in SYSTEM_ROLES:
            groups[role], _created = Group.objects.get_or_create(name=role)

        for user_data in TEST_USERS:
            role = user_data["role"]
            user, created = User.objects.get_or_create(
                username=user_data["username"],
                defaults={
                    "email": user_data["email"],
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                },
            )

            if created or reset_passwords:
                user.set_password(password)

            user.email = user_data["email"]
            user.first_name = user_data["first_name"]
            user.last_name = user_data["last_name"]
            user.is_staff = False
            user.save()

            user.groups.set([groups[role]])
            UserProfile.objects.update_or_create(user=user, defaults={"company": company})

            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action} {role} test user: {user.username} / {password}"
                )
            )
