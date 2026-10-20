from django.urls import path
from . import views

urlpatterns = [
    # Rider & Customer routes
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("select-ride/", views.select_ride, name="select_ride"),
    path("booking-confirm/", views.booking_confirm, name="booking_confirm"),
    path("create-booking/", views.create_booking, name="create_booking"),
    path("searching-driver/<int:ride_id>/", views.searching_driver, name="searching_driver"),
    path("assign-driver/<int:ride_id>/", views.assign_driver, name="assign_driver"),
    path("driver-assigned/<int:ride_id>/", views.driver_assigned, name="driver_assigned"),
    path("start-ride/<int:ride_id>/", views.start_ride, name="start_ride"),
    path("complete-ride/<int:ride_id>/", views.complete_ride, name="complete_ride"),
    path("cancel-ride/<int:ride_id>/", views.cancel_ride, name="cancel_ride"),
    path("rate-ride/<int:ride_id>/", views.rate_ride, name="rate_ride"),
    path("ride-detail/<int:ride_id>/", views.ride_detail, name="ride_detail"),
    path("my-rides/", views.my_rides, name="my_rides"),
    path("profile/", views.profile, name="profile"),

    # Captain (Driver/Rider) Lifecycle
    path("captain/register/", views.captain_register_view, name="captain_register"),
    path("captain/login/", views.captain_login_view, name="captain_login"),
    path("captain/status/", views.captain_status_view, name="captain_status"),
    path("captain/dashboard/", views.captain_dashboard_view, name="captain_dashboard"),
    path("captain/toggle-status/", views.captain_toggle_status_view, name="captain_toggle_status"),
    path("captain/accept-ride/<int:ride_id>/", views.captain_accept_ride_view, name="captain_accept_ride"),
    path("captain/arrived/<int:ride_id>/", views.captain_arrived_pickup_view, name="captain_arrived"),
    path("captain/verify-otp/<int:ride_id>/", views.captain_verify_otp_view, name="captain_verify_otp"),
    path("captain/complete/<int:ride_id>/", views.captain_complete_ride_view, name="captain_complete"),

    # Admin Captain Verification & Permit Portal
    path("admin-portal/captains/", views.admin_portal_view, name="admin_portal"),
    path("admin-portal/permit/<int:driver_id>/approve/", views.admin_approve_captain_view, name="admin_approve_captain"),
    path("admin-portal/permit/<int:driver_id>/reject/", views.admin_reject_captain_view, name="admin_reject_captain"),
    path("admin-portal/permit/<int:driver_id>/suspend/", views.admin_suspend_captain_view, name="admin_suspend_captain"),
    path("admin-portal/quick-login/", views.admin_quick_login_view, name="admin_quick_login"),

    # Admin Business Dashboard & Pricing Control
    path("admin-portal/dashboard/", views.admin_business_dashboard_view, name="admin_business_dashboard"),
    path("admin-portal/pricing/update/", views.admin_update_pricing_view, name="admin_update_pricing"),

    # Real Map API
    path("api/nearby-captains/", views.api_nearby_captains_view, name="api_nearby_captains"),
]