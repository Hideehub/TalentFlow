from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.choices import RECRUITMENT_ROLES, ROLE_RECRUITER
from accounts.decorators import role_required, user_has_role

from .forms import CandidateImportForm
from .services import CandidateImportError, candidate_import_confirm, candidate_import_preview

PREVIEW_SESSION_KEY = "candidate_import_preview"


@role_required(*RECRUITMENT_ROLES)
def candidate_import_view(request):
    form = CandidateImportForm()
    preview = None

    if request.method == "POST":
        form = CandidateImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                preview = candidate_import_preview(form.cleaned_data["file"], user=request.user)
            except CandidateImportError as exc:
                form.add_error("file", str(exc))
            else:
                request.session[PREVIEW_SESSION_KEY] = preview

    return render(
        request,
        "uploads/candidate_import.html",
        {"form": form, "preview": preview},
    )


@role_required(*RECRUITMENT_ROLES)
def candidate_import_confirm_view(request):
    if request.method != "POST":
        return redirect("uploads:candidate_import")

    preview = request.session.get(PREVIEW_SESSION_KEY)
    if not preview:
        messages.error(request, "Upload and preview a file before importing.")
        return redirect("uploads:candidate_import")

    assigned_recruiter = request.user if user_has_role(request.user, (ROLE_RECRUITER,)) else None
    result = candidate_import_confirm(
        preview["rows"],
        user=request.user,
        assigned_recruiter=assigned_recruiter,
    )
    request.session.pop(PREVIEW_SESSION_KEY, None)

    messages.success(
        request,
        f"Imported {result['imported']} candidate(s). Skipped {result['skipped']}.",
    )
    return redirect("recruitment:candidate_list")
