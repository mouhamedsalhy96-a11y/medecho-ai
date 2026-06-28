from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render

from .services.costing import build_user_cost_summary


def is_superuser(user):
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(is_superuser, login_url="billing")
def cost_dashboard(request):
    summary = build_user_cost_summary(request.user)
    return render(request, "core/cost_dashboard.html", summary)
