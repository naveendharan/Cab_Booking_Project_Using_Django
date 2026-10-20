from django.test import TestCase, Client
from django.contrib.auth.models import User
from booking.models import Driver, Ride
from decimal import Decimal


class RideBookingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="rider_jane",
            password="Password123!",
            email="jane@example.com"
        )
        self.driver_user = User.objects.create_user(
            username="captain_sam",
            password="CaptainPass123!"
        )
        self.driver = Driver.objects.create(
            user=self.driver_user,
            name="Sam Captain",
            phone="+91 9988776655",
            vehicle_type="bike",
            vehicle_model="Honda Activa 6G",
            vehicle_number="KA 04 XY 1234",
            license_number="KA-04-2020-0012988",
            rc_number="RC-KA04-123456",
            city="Bengaluru",
            is_verified=True,
            verification_status="approved",
            rating=Decimal("4.9"),
            is_available=True
        )
        self.admin_user = User.objects.create_superuser(
            username="admin_naveen",
            password="AdminPassword123!",
            email="admin@example.com"
        )

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RideGo")
        self.assertContains(response, "real-home-map")

    def test_full_ride_booking_flow(self):
        # 1. Login
        login_success = self.client.login(username="rider_jane", password="Password123!")
        self.assertTrue(login_success)

        # 2. Select Ride
        response = self.client.post("/select-ride/", {
            "pickup": "Indiranagar",
            "destination": "MG Road",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bike Captain")

        # 3. Confirm Ride
        response = self.client.post("/booking-confirm/", {
            "ride_type": "bike",
        })
        self.assertEqual(response.status_code, 200)

        # 4. Create Booking
        response = self.client.post("/create-booking/", {
            "ride_type": "bike",
            "payment_method": "cash",
        })
        self.assertEqual(response.status_code, 302)
        ride = Ride.objects.filter(user=self.user).first()
        self.assertIsNotNone(ride)
        self.assertEqual(ride.status, "searching")
        self.assertEqual(len(ride.otp), 4)

        # 5. Searching Driver page
        response = self.client.get(f"/searching-driver/{ride.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "searching-radar-map")

        # 6. Assign Driver
        response = self.client.get(f"/assign-driver/{ride.id}/")
        self.assertEqual(response.status_code, 302)
        ride.refresh_from_db()
        self.assertEqual(ride.status, "assigned")
        self.assertEqual(ride.driver, self.driver)

        # 7. Driver Assigned page shows OTP and real map
        response = self.client.get(f"/driver-assigned/{ride.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ride.otp)
        self.assertContains(response, "enroute-map")

        # 8. Start Ride
        response = self.client.get(f"/start-ride/{ride.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "transit-map")
        ride.refresh_from_db()
        self.assertEqual(ride.status, "started")

        # 9. Complete Ride
        response = self.client.get(f"/complete-ride/{ride.id}/")
        self.assertEqual(response.status_code, 200)
        ride.refresh_from_db()
        self.assertEqual(ride.status, "completed")
        self.assertEqual(ride.payment_status, "Paid")

        # 10. Rate Ride
        response = self.client.post(f"/rate-ride/{ride.id}/", {
            "rating": "5",
            "feedback": "Smooth ride!",
        })
        self.assertEqual(response.status_code, 302)
        ride.refresh_from_db()
        self.assertEqual(ride.rating, 5)

        # 11. My Rides
        response = self.client.get("/my-rides/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Completed")

    def test_captain_registration_and_pending_status(self):
        # Apply as new captain
        response = self.client.post("/captain/register/", {
            "name": "Karan Varma",
            "username": "captain_karan",
            "phone": "+91 91234 56789",
            "email": "karan@example.com",
            "password": "CaptainPass123!",
            "vehicle_type": "bike",
            "vehicle_model": "Bajaj Pulsar 150",
            "vehicle_number": "KA 05 MN 9922",
            "license_number": "KA-05-2023-0099182",
            "rc_number": "RC-KA05-992200",
            "city": "Bengaluru",
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/captain/status/")

        new_driver = Driver.objects.get(user__username="captain_karan")
        self.assertFalse(new_driver.is_verified)
        self.assertEqual(new_driver.verification_status, "pending")
        self.assertFalse(new_driver.is_permitted)

        # Captain Status page shows pending state
        response = self.client.get("/captain/status/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inspection In Progress")

        # Attempt to access Captain Cockpit while pending should redirect to status
        cockpit_res = self.client.get("/captain/dashboard/")
        self.assertEqual(cockpit_res.status_code, 302)
        self.assertRedirects(cockpit_res, "/captain/status/")

    def test_admin_approval_and_permit_granting(self):
        # Create unverified captain
        unverified_user = User.objects.create_user(username="captain_test", password="Pass123!")
        unverified_driver = Driver.objects.create(
            user=unverified_user,
            name="Test Driver",
            phone="+91 90000 00000",
            vehicle_type="cab",
            vehicle_number="KA 03 AA 1111",
            license_number="KA-03-2021-0081234",
            verification_status="pending",
            is_verified=False
        )

        # Login as Admin
        self.client.login(username="admin_naveen", password="AdminPassword123!")
        portal_res = self.client.get("/admin-portal/captains/")
        self.assertEqual(portal_res.status_code, 200)
        self.assertContains(portal_res, "Captain Verification & Permit Portal")
        self.assertContains(portal_res, "KA-03-2021-0081234")

        # Admin approves the captain
        approve_res = self.client.get(f"/admin-portal/permit/{unverified_driver.id}/approve/")
        self.assertEqual(approve_res.status_code, 302)
        unverified_driver.refresh_from_db()
        self.assertTrue(unverified_driver.is_verified)
        self.assertEqual(unverified_driver.verification_status, "approved")
        self.assertTrue(unverified_driver.is_permitted)

        # Now Captain can access Cockpit
        self.client.login(username="captain_test", password="Pass123!")
        cockpit_res = self.client.get("/captain/dashboard/")
        self.assertEqual(cockpit_res.status_code, 200)
        self.assertContains(cockpit_res, "Captain Cockpit")
        self.assertContains(cockpit_res, "Permitted ✓")

    def test_admin_rejection_flow(self):
        unverified_user = User.objects.create_user(username="captain_flawed", password="Pass123!")
        flawed_driver = Driver.objects.create(
            user=unverified_user,
            name="Flawed Driver",
            phone="+91 91111 11111",
            vehicle_type="auto",
            vehicle_number="KA 01 ZZ 0000",
            license_number="INVALID_DL",
            verification_status="pending",
            is_verified=False
        )

        # Login as admin and reject with note
        self.client.login(username="admin_naveen", password="AdminPassword123!")
        reject_res = self.client.post(f"/admin-portal/permit/{flawed_driver.id}/reject/", {
            "rejection_reason": "Driving license number is fraudulent."
        })
        self.assertEqual(reject_res.status_code, 302)
        flawed_driver.refresh_from_db()
        self.assertFalse(flawed_driver.is_verified)
        self.assertEqual(flawed_driver.verification_status, "rejected")
        self.assertEqual(flawed_driver.rejection_reason, "Driving license number is fraudulent.")

        # Flawed driver logs in and sees rejection reason
        self.client.login(username="captain_flawed", password="Pass123!")
        status_res = self.client.get("/captain/status/")
        self.assertEqual(status_res.status_code, 200)
        self.assertContains(status_res, "Application Rejected")
        self.assertContains(status_res, "Driving license number is fraudulent.")

    def test_api_nearby_captains(self):
        response = self.client.get("/api/nearby-captains/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("captains", data)
        self.assertGreaterEqual(data["count"], 1)

    def test_admin_business_dashboard_access_control(self):
        # 1. Unauthenticated or non-staff user gets access required
        response = self.client.get("/admin-portal/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Authentication Required")

        # 2. Superuser/Staff gets full executive dashboard
        self.client.login(username="admin_naveen", password="AdminPassword123!")
        res = self.client.get("/admin-portal/dashboard/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Rides, Profit & Dynamic Pricing Dashboard")
        self.assertContains(res, "Gross Bookings")
        self.assertContains(res, "Platform Net Profit")
        self.assertContains(res, "Dynamic Pricing & Margin Management")

    def test_dynamic_pricing_live_update_affects_fares(self):
        from booking.models import PricingPlan
        from booking.views import get_active_fare_rates

        get_active_fare_rates()
        bike_plan = PricingPlan.objects.get(vehicle_type="bike")

        # Admin logs in and updates Bike pricing live
        self.client.login(username="admin_naveen", password="AdminPassword123!")
        post_data = {
            "action": "update_single",
            "plan_id": bike_plan.id,
            "base_fare": "50.00",
            "per_km_rate": "15.00",
            "commission_percentage": "25.00",
            "surge_multiplier": "1.20",
            "is_active": "on",
        }
        res = self.client.post("/admin-portal/pricing/update/", post_data)
        self.assertEqual(res.status_code, 302)

        bike_plan.refresh_from_db()
        self.assertEqual(bike_plan.base_fare, Decimal("50.00"))
        self.assertEqual(bike_plan.per_km_rate, Decimal("15.00"))
        self.assertEqual(bike_plan.commission_percentage, Decimal("25.00"))
        self.assertEqual(bike_plan.surge_multiplier, Decimal("1.20"))

        # Rider books bike ride and confirms it uses updated live rates
        self.client.login(username="rider_jane", password="Password123!")
        res = self.client.post("/select-ride/", {
            "pickup": "Indiranagar",
            "destination": "Koramangala",
        })
        self.assertEqual(res.status_code, 200)
        # Session should reflect distance and fare calculated with updated rates
        dist = Decimal(str(self.client.session.get("distance", 5.0)))
        expected_raw = (Decimal("50.00") + (dist * Decimal("15.00"))) * Decimal("1.20")
        expected_fare = max(Decimal("50.00"), round(expected_raw))
        self.assertEqual(Decimal(str(self.client.session.get("fares", {})["bike"])), expected_fare)

    def test_ride_profit_and_captain_earnings_accounting(self):
        # Rider books and completes ride
        self.client.login(username="rider_jane", password="Password123!")
        self.client.post("/select-ride/", {"pickup": "MG Road", "destination": "Indiranagar"})
        self.client.post("/booking-confirm/", {"ride_type": "bike"})
        self.client.post("/create-booking/", {"ride_type": "bike", "payment_method": "cash"})

        ride = Ride.objects.filter(user=self.user).latest("id")
        self.assertGreater(ride.estimated_fare, Decimal("0.00"))
        self.assertGreater(ride.platform_profit, Decimal("0.00"))
        self.assertGreater(ride.captain_earnings, Decimal("0.00"))
        self.assertEqual(ride.platform_profit + ride.captain_earnings, ride.estimated_fare)

        # Assign captain and complete
        ride.driver = self.driver
        ride.status = "started"
        ride.save()

        initial_earnings = self.driver.earnings
        self.client.get(f"/complete-ride/{ride.id}/")

        self.driver.refresh_from_db()
        self.assertEqual(self.driver.earnings, initial_earnings + ride.captain_earnings)

    def test_admin_quick_surge_action(self):
        from booking.models import PricingPlan
        from booking.views import get_active_fare_rates

        get_active_fare_rates()
        self.client.login(username="admin_naveen", password="AdminPassword123!")

        # Apply Rain surge
        res = self.client.post("/admin-portal/pricing/update/", {
            "action": "quick_surge",
            "preset": "rain",
        })
        self.assertEqual(res.status_code, 302)
        for p in PricingPlan.objects.all():
            self.assertEqual(p.surge_multiplier, Decimal("1.40"))

        # Reset to normal
        res = self.client.post("/admin-portal/pricing/update/", {
            "action": "quick_surge",
            "preset": "normal",
        })
        self.assertEqual(res.status_code, 302)
        for p in PricingPlan.objects.all():
            self.assertEqual(p.surge_multiplier, Decimal("1.00"))

