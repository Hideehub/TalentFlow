import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .choices import ROLE_RECRUITER
from .models import Company, UserProfile


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    name = factory.Sequence(lambda n: f"Company {n}")


class UserFactory(factory.django.DjangoModelFactory):
    """User with a role group and a UserProfile.

    UserFactory(role=ROLE_HR_ADMIN, company=acme)
    role="" gives a user with no group; company=False gives a user with no profile.
    """

    class Meta:
        model = get_user_model()
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda user: f"{user.username}@example.com")
    password = factory.django.Password("password123")

    @factory.post_generation
    def role(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted is None:
            extracted = ROLE_RECRUITER
        if extracted:
            group, _created = Group.objects.get_or_create(name=extracted)
            self.groups.add(group)

    @factory.post_generation
    def company(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted is None:
            extracted = CompanyFactory()
        if extracted:
            UserProfile.objects.create(user=self, company=extracted)
