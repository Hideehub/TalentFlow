import factory

from accounts.factories import CompanyFactory

from .models import Application, Candidate, JobOpening


class JobOpeningFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = JobOpening

    company = factory.SubFactory(CompanyFactory)
    title = factory.Sequence(lambda n: f"Job {n}")
    department = "Engineering"
    status = "open"


class CandidateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Candidate

    company = factory.SubFactory(CompanyFactory)
    full_name = factory.Sequence(lambda n: f"Candidate {n}")
    email = factory.Sequence(lambda n: f"candidate{n}@example.com")
    phone = "08000000000"


class ApplicationFactory(factory.django.DjangoModelFactory):
    """Application whose candidate belongs to the job's company.

    ApplicationFactory(job=None) gives an import-style application with no job.
    """

    class Meta:
        model = Application

    job = factory.SubFactory(JobOpeningFactory)
    candidate = factory.SubFactory(
        CandidateFactory,
        company=factory.LazyAttribute(
            lambda candidate: candidate.factory_parent.job.company
            if candidate.factory_parent.job
            else CompanyFactory()
        ),
    )
    imported_position = factory.LazyAttribute(
        lambda application: "" if application.job else "Imported role"
    )
