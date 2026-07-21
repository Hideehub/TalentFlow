from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.shortcuts import redirect, render

from .forms import SignUpForm
from .models import Company, UserProfile


def signup_view(request):
    form = SignUpForm()

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            company, _created = Company.objects.get_or_create(
                name=form.cleaned_data["company_name"]
            )
            UserProfile.objects.create(user=user, company=company)
            group, _created = Group.objects.get_or_create(name=form.cleaned_data["role"])
            user.groups.add(group)
            login(request, user)
            return redirect("dashboard:home")

    return render(request, "accounts/signup.html", {"form": form})
