from .models import Driver

def captain_context(request):
    data = {
        "pending_captains_count": 0,
        "user_is_captain": False,
        "user_captain_profile": None,
    }
    try:
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                data["pending_captains_count"] = Driver.objects.filter(verification_status="pending").count()
            if hasattr(request.user, "driver_profile"):
                data["user_is_captain"] = True
                data["user_captain_profile"] = request.user.driver_profile
    except Exception:
        pass
    return data
