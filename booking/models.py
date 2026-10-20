from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
import random


class Driver(models.Model):

    VEHICLE_CHOICES = [
        ("bike", "Bike Captain"),
        ("auto", "Auto Rickshaw"),
        ("cab", "Cab Economy"),
    ]

    VERIFICATION_STATUS_CHOICES = [
        ("pending", "Pending Verification"),
        ("approved", "Approved / Permitted"),
        ("rejected", "Rejected"),
        ("suspended", "Suspended"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="driver_profile"
    )

    name = models.CharField(max_length=100, blank=True, default="")

    phone = models.CharField(max_length=15)

    vehicle_type = models.CharField(
        max_length=20,
        choices=VEHICLE_CHOICES
    )

    vehicle_model = models.CharField(
        max_length=100,
        default="Standard",
        help_text="e.g. Honda Activa 6G, Bajaj RE, Maruti Swift"
    )

    vehicle_number = models.CharField(max_length=20)

    license_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Driving License Number"
    )

    rc_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Vehicle Registration Certificate Number"
    )

    city = models.CharField(
        max_length=50,
        default="Bengaluru"
    )

    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default="pending"
    )

    is_verified = models.BooleanField(
        default=False,
        help_text="Designates whether this captain has been verified and permitted by admin."
    )

    rejection_reason = models.TextField(
        blank=True,
        default="",
        help_text="Reason provided by admin if application is rejected"
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_captains"
    )

    is_available = models.BooleanField(default=True)

    current_lat = models.FloatField(default=12.9716)

    current_lng = models.FloatField(default=77.5946)

    earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=4.9
    )

    total_rides = models.PositiveIntegerField(default=120)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        display = self.name or self.user.username
        status = self.get_verification_status_display()
        return f"{display} ({self.get_vehicle_type_display()}) - {self.vehicle_number} [{status}]"

    @property
    def display_name(self):
        return self.name or self.user.get_full_name() or self.user.username

    @property
    def is_permitted(self):
        return self.is_verified and self.verification_status == "approved"

    @property
    def can_drive(self):
        return self.is_permitted and self.is_available


class Ride(models.Model):

    RIDE_TYPES = [
        ("bike", "Bike Captain"),
        ("auto", "Auto Rickshaw"),
        ("cab", "Cab Economy"),
    ]

    STATUS_CHOICES = [
        ("searching", "Searching Driver"),
        ("assigned", "Driver Assigned"),
        ("started", "Ride Started"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_CHOICES = [
        ("cash", "Cash"),
        ("upi", "UPI / QR"),
        ("wallet", "RideGo Wallet"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="rides"
    )

    driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rides"
    )

    pickup = models.CharField(max_length=255)
    pickup_lat = models.FloatField(default=12.9784)
    pickup_lng = models.FloatField(default=77.6408)

    destination = models.CharField(max_length=255)
    destination_lat = models.FloatField(default=12.9352)
    destination_lng = models.FloatField(default=77.6245)

    ride_type = models.CharField(
        max_length=20,
        choices=RIDE_TYPES
    )

    distance = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=5.00
    )

    estimated_fare = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    otp = models.CharField(
        max_length=4,
        default="4321",
        help_text="4-digit OTP for captain ride verification"
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default="cash"
    )

    payment_status = models.CharField(
        max_length=20,
        default="Pending"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="searching"
    )

    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )

    feedback = models.TextField(
        blank=True,
        default=""
    )

    surge_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("1.00")
    )

    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("20.00"),
        help_text="Platform commission rate applied to this ride"
    )

    platform_profit = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Net profit earned by the platform for this ride"
    )

    captain_earnings = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Net earnings payout to the captain"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        if not self.otp or self.otp == "4321":
            self.otp = str(random.randint(1000, 9999))
        if self.status == "completed" and self.estimated_fare:
            rate = self.commission_rate or Decimal("20.00")
            if not self.platform_profit or self.platform_profit == 0:
                self.platform_profit = round(self.estimated_fare * (rate / Decimal("100.00")), 2)
            if not self.captain_earnings or self.captain_earnings == 0:
                self.captain_earnings = self.estimated_fare - self.platform_profit
        super().save(*args, **kwargs)

    @property
    def calculated_profit(self):
        if self.platform_profit and self.platform_profit > 0:
            return self.platform_profit
        rate = self.commission_rate if self.commission_rate else Decimal("20.00")
        return round(self.estimated_fare * (rate / Decimal("100.00")), 2)

    @property
    def calculated_captain_earnings(self):
        if self.captain_earnings and self.captain_earnings > 0:
            return self.captain_earnings
        return self.estimated_fare - self.calculated_profit

    @property
    def icon(self):
        icons = {
            "bike": "🏍️",
            "auto": "🛺",
            "cab": "🚕",
        }
        return icons.get(self.ride_type, "🚗")

    def __str__(self):
        return f"Ride #{self.id} ({self.user.username}) - {self.pickup} to {self.destination} [{self.status}]"

    class Meta:
        ordering = ["-created_at"]


class PricingPlan(models.Model):

    VEHICLE_CHOICES = [
        ("bike", "Bike Captain"),
        ("auto", "Auto Rickshaw"),
        ("cab", "Cab Economy"),
    ]

    vehicle_type = models.CharField(
        max_length=20,
        choices=VEHICLE_CHOICES,
        unique=True
    )

    name = models.CharField(max_length=100)

    icon = models.CharField(max_length=10, default="🚗")

    base_fare = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("30.00"),
        help_text="Base pickup fare in ₹"
    )

    per_km_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("8.00"),
        help_text="Per kilometer rate in ₹/km"
    )

    commission_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("20.00"),
        help_text="Platform profit commission percentage cut (e.g. 20.00%)"
    )

    surge_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("1.00"),
        help_text="Surge pricing factor (1.00x normal, 1.25x peak, 1.50x rain)"
    )

    time_estimate = models.CharField(max_length=50, default="2-4 min")

    badge = models.CharField(max_length=50, default="FASTEST")

    description = models.TextField(blank=True, default="")

    capacity = models.CharField(max_length=50, default="1 person")

    is_active = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Base: ₹{self.base_fare}, ₹{self.per_km_rate}/km, Comm: {self.commission_percentage}%, Surge: {self.surge_multiplier}x)"

    def calculate_fare(self, distance_km: Decimal) -> Decimal:
        base = self.base_fare + (Decimal(str(distance_km)) * self.per_km_rate)
        total = base * self.surge_multiplier
        return round(total, 2)

    class Meta:
        ordering = ["vehicle_type"]