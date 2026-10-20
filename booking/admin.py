from django.contrib import admin
from .models import Driver, Ride, PricingPlan


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "user",
        "vehicle_type",
        "vehicle_model",
        "vehicle_number",
        "license_number",
        "verification_status",
        "is_verified",
        "is_available",
        "rating",
    )

    list_filter = (
        "verification_status",
        "is_verified",
        "vehicle_type",
        "is_available",
    )

    search_fields = (
        "name",
        "user__username",
        "phone",
        "vehicle_number",
        "vehicle_model",
        "license_number",
        "rc_number",
    )

    actions = ["approve_captains", "reject_captains", "suspend_captains"]

    @admin.action(description="✓ Verify & Permit Selected Captains")
    def approve_captains(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            verification_status="approved",
            is_verified=True,
            verified_at=timezone.now(),
            verified_by=request.user
        )
        self.message_user(request, f"{updated} Captain(s) approved and issued permits successfully.")

    @admin.action(description="✗ Reject Selected Captain Applications")
    def reject_captains(self, request, queryset):
        updated = queryset.update(
            verification_status="rejected",
            is_verified=False,
            is_available=False
        )
        self.message_user(request, f"{updated} Captain application(s) marked as rejected.")

    @admin.action(description="⏸ Suspend Selected Captain Permits")
    def suspend_captains(self, request, queryset):
        updated = queryset.update(
            verification_status="suspended",
            is_verified=False,
            is_available=False
        )
        self.message_user(request, f"{updated} Captain permit(s) suspended.")


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "driver",
        "pickup",
        "destination",
        "ride_type",
        "estimated_fare",
        "platform_profit",
        "commission_rate",
        "otp",
        "status",
        "payment_method",
        "created_at",
    )

    list_filter = (
        "ride_type",
        "status",
        "payment_method",
    )

    search_fields = (
        "user__username",
        "pickup",
        "destination",
        "otp",
    )


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "vehicle_type",
        "base_fare",
        "per_km_rate",
        "commission_percentage",
        "surge_multiplier",
        "is_active",
        "updated_at",
    )

    list_editable = (
        "base_fare",
        "per_km_rate",
        "commission_percentage",
        "surge_multiplier",
        "is_active",
    )

    list_filter = (
        "vehicle_type",
        "is_active",
    )