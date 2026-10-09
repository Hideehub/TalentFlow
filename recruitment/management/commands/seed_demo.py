"""Create the public demo company. Safe to rerun: existing records are reused, and
history, notes and interviews are only added for applications created by this run."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.demo import DEMO_COMPANY_NAME, DEMO_USERS
from accounts.models import Company, UserProfile
from recruitment.models import (
    Application,
    ApplicationNote,
    ApplicationStatusChange,
    Candidate,
    Interview,
    InterviewFeedback,
    JobOpening,
)

# key, title, department, location, employment type, status, has hiring manager, description
JOBS = [
    ("icu_nurse", "Registered Nurse, ICU", "Clinical", "Seattle, WA", "full_time", "open", True,
     "Provide critical care to adult ICU patients on a 12-bed unit. BLS and ACLS required."),
    ("backend", "Senior Backend Engineer", "Engineering", "Remote", "full_time", "open", True,
     "Build the APIs behind our patient scheduling and records platform. Python and Postgres."),
    ("analyst", "Data Analyst", "Analytics", "Hybrid, Seattle", "hybrid", "open", False,
     "Turn clinical operations data into dashboards and weekly insights for leadership."),
    ("reception", "Medical Receptionist", "Operations", "Tacoma, WA", "part_time", "open", False,
     "Be the first point of contact for patients at our Tacoma clinic."),
    ("designer", "Product Designer", "Design", "Remote", "contract", "on_hold", True,
     "Design patient-facing booking flows. Six-month contract."),
    ("intern", "Finance Intern", "Finance", "Seattle, WA", "internship", "closed", False,
     "Summer internship supporting month-end close and budgeting."),
    ("pharmacist", "Clinical Pharmacist", "Clinical", "Seattle, WA", "full_time", "draft", True,
     "Draft role: medication reviews across inpatient units."),
]

# full name, email, phone, years of experience, source, gets a sample resume
CANDIDATES = [
    ("Maya Patel", "maya.patel@example.com", "+1 206 555 0101", 6, "referral", True),
    ("Daniel Kim", "daniel.kim@example.com", "+1 206 555 0102", 9, "linkedin", True),
    ("Sofia Alvarez", "sofia.alvarez@example.com", "+1 206 555 0103", 3, "career_site", True),
    ("James O'Connor", "james.oconnor@example.com", "+1 206 555 0104", 12, "agency", False),
    ("Aisha Bello", "aisha.bello@example.com", "+1 206 555 0105", 4, "job_board", True),
    ("Tom Nguyen", "tom.nguyen@example.com", "+1 206 555 0106", 1, "career_site", False),
    ("Priya Raman", "priya.raman@example.com", "+1 206 555 0107", 7, "linkedin", True),
    ("Lucas Martin", "lucas.martin@example.com", "+1 206 555 0108", 2, "job_board", False),
    ("Grace Liu", "grace.liu@example.com", "+1 206 555 0109", 5, "referral", False),
    ("Omar Haddad", "omar.haddad@example.com", "+1 206 555 0110", 8, "import", False),
    ("Hannah Becker", "hannah.becker@example.com", "+1 206 555 0111", 0, "career_site", False),
    ("Kwame Mensah", "kwame.mensah@example.com", "+1 206 555 0112", 10, "import", False),
]

# email, job key (None = imported without a matching job), imported position, status,
# owned by the demo recruiter, days since applying
APPLICATIONS = [
    ("maya.patel@example.com", "icu_nurse", "", "hired", True, 40),
    ("daniel.kim@example.com", "backend", "", "offer", True, 30),
    ("sofia.alvarez@example.com", "backend", "", "interview", True, 14),
    ("sofia.alvarez@example.com", "analyst", "", "screening", True, 10),
    ("james.oconnor@example.com", "icu_nurse", "", "assessment", False, 21),
    ("aisha.bello@example.com", "analyst", "", "interview", False, 12),
    ("tom.nguyen@example.com", "reception", "", "applied", False, 2),
    ("priya.raman@example.com", "backend", "", "rejected", True, 25),
    ("lucas.martin@example.com", "reception", "", "screening", True, 6),
    ("grace.liu@example.com", "designer", "", "applied", False, 9),
    ("omar.haddad@example.com", None, "Radiology Technician", "screening", False, 18),
    ("hannah.becker@example.com", "intern", "", "rejected", False, 50),
    ("kwame.mensah@example.com", None, "Facilities Manager", "applied", False, 15),
]

PIPELINE = ["applied", "screening", "interview", "assessment", "offer", "hired"]
INTERVIEWED = {"interview", "assessment", "offer", "hired"}
RECOMMENDATION = {"interview": "yes", "assessment": "yes", "offer": "strong_yes", "hired": "strong_yes"}


def status_path(status):
    if status == "rejected":
        return ["applied", "screening", "rejected"]
    return PIPELINE[: PIPELINE.index(status) + 1]


def _pdf_text(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def sample_resume_pdf(name, headline):
    """A tiny valid one-page PDF, so demo downloads work without bundling files."""
    lines = [name, headline, "Sample resume generated for the TalentFlow demo."]
    content = "BT /F1 14 Tf 72 720 Td " + " ".join(
        f"({_pdf_text(line)}) Tj 0 -24 Td" for line in lines
    ) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref_at = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    pdf += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return pdf


def _backdate(model, pk, when, **extra):
    model.objects.filter(pk=pk).update(created_at=when, updated_at=when, **extra)


class Command(BaseCommand):
    help = "Create (or top up) the demo company used by the one-click demo logins."

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        company, _created = Company.objects.get_or_create(name=DEMO_COMPANY_NAME)
        users = {key: self._demo_user(company, account) for key, account in DEMO_USERS.items()}
        recruiter = users["recruiter"]
        manager = users["hiring-manager"]
        hr_admin = users["hr-admin"]

        jobs = {}
        for key, title, department, location, kind, status, managed, description in JOBS:
            jobs[key], _created = JobOpening.objects.get_or_create(
                company=company,
                title=title,
                defaults={
                    "department": department,
                    "location": location,
                    "employment_type": kind,
                    "status": status,
                    "hiring_manager": manager if managed else None,
                    "description": description,
                },
            )

        candidates = {}
        for full_name, email, phone, years, source, has_resume in CANDIDATES:
            candidate, _created = Candidate.objects.get_or_create(
                company=company,
                email=email,
                defaults={
                    "full_name": full_name,
                    "phone": phone,
                    "years_of_experience": years,
                    "source": source,
                },
            )
            if has_resume and not candidate.resume:
                headline = f"{years} years of experience"
                candidate.resume.save(
                    f"{full_name.lower().replace(' ', '-')}-resume.pdf",
                    ContentFile(sample_resume_pdf(full_name, headline)),
                    save=False,
                )
                candidate.resume_original_name = f"{full_name} - Resume.pdf"
                candidate.resume_uploaded_at = now
                candidate.save()
            candidates[email] = candidate

        created_count = 0
        for email, job_key, imported, status, owned, days_ago in APPLICATIONS:
            job = jobs[job_key] if job_key else None
            lookup = {"candidate": candidates[email], "job": job}
            if job is None:
                lookup["imported_position"] = imported
            application, created = Application.objects.get_or_create(
                **lookup,
                defaults={"status": status, "assigned_recruiter": recruiter if owned else None},
            )
            if created:
                created_count += 1
                applied_at = now - timedelta(days=days_ago)
                _backdate(Application, application.pk, applied_at, date_applied=applied_at.date())
                actor = recruiter if owned else hr_admin
                self._history(application, status, applied_at, now, actor)
                self._notes(application, applied_at, actor, manager)
                self._interviews(application, applied_at, now, manager, hr_admin)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo company '{company.name}' ready: {len(jobs)} jobs, "
                f"{len(candidates)} candidates, {created_count} new applications."
            )
        )

    def _demo_user(self, company, account):
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=account["username"],
            defaults={
                "first_name": account["first_name"],
                "last_name": account["last_name"],
                "email": f"{account['username']}@northwind.example",
            },
        )
        profile = getattr(user, "profile", None)
        if not created and (
            user.has_usable_password() or (profile and profile.company_id != company.id)
        ):
            # A real account already uses this name; never take it over.
            raise CommandError(f"User '{user.username}' exists and is not a demo account.")

        user.set_unusable_password()
        user.is_staff = False
        user.is_superuser = False
        user.save()
        group, _created = Group.objects.get_or_create(name=account["role"])
        user.groups.set([group])
        UserProfile.objects.update_or_create(user=user, defaults={"company": company})
        return user

    def _history(self, application, status, applied_at, now, actor):
        path = status_path(status)
        step = (now - timedelta(days=1) - applied_at) / max(len(path), 1)
        previous = ""
        for index, to_status in enumerate(path):
            change = ApplicationStatusChange.objects.create(
                application=application,
                from_status=previous,
                to_status=to_status,
                changed_by=actor,
            )
            _backdate(ApplicationStatusChange, change.pk, applied_at + step * index)
            previous = to_status

    def _notes(self, application, applied_at, actor, manager):
        if application.status == "applied":
            return
        note = ApplicationNote.objects.create(
            application=application,
            author=actor,
            note="Phone screen done. Clear communicator, relevant experience, keen on the role.",
        )
        _backdate(ApplicationNote, note.pk, applied_at + timedelta(days=2))
        if application.job and application.job.hiring_manager_id == manager.id:
            note = ApplicationNote.objects.create(
                application=application,
                author=manager,
                note="Reviewed the profile. Happy to move forward; please book a technical round.",
            )
            _backdate(ApplicationNote, note.pk, applied_at + timedelta(days=3))

    def _interviews(self, application, applied_at, now, manager, hr_admin):
        if application.status not in INTERVIEWED:
            return
        managed = application.job and application.job.hiring_manager_id == manager.id
        interviewer = manager if managed else hr_admin
        held_at = applied_at + (now - applied_at) / 2
        interview = Interview.objects.create(
            application=application,
            title="First-round interview",
            scheduled_at=held_at,
            location="Video call",
            interviewer=interviewer,
            status="completed",
        )
        feedback = InterviewFeedback.objects.create(
            interview=interview,
            author=interviewer,
            recommendation=RECOMMENDATION[application.status],
            comments="Strong examples from previous roles and good questions about the team.",
        )
        _backdate(InterviewFeedback, feedback.pk, held_at + timedelta(hours=2))

        if application.status == "interview":
            # One done but awaiting feedback (shows on the dashboard), one coming up.
            Interview.objects.create(
                application=application,
                title="Technical interview",
                scheduled_at=now - timedelta(hours=20),
                location="On site",
                interviewer=interviewer,
                status="scheduled",
            )
            Interview.objects.create(
                application=application,
                title="Final interview",
                scheduled_at=now + timedelta(days=3),
                location="On site",
                interviewer=hr_admin,
                status="scheduled",
            )
