from django.shortcuts import render

from recruitment.models import JobOpening


def landing_page(request):
    open_jobs = JobOpening.objects.filter(status="open").order_by("-created_at")[:3]
    return render(request, "core/landing.html", {"open_jobs": open_jobs})
