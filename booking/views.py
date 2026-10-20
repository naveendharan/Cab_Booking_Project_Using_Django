from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal
import random
import json

from django.db.models import Sum, Count, Avg
from .models import Ride, Driver, PricingPlan


def get_active_fare_rates():
    """Dynamically loads pricing plans from database. Auto-seeds defaults if table is empty."""
    plans = list(PricingPlan.objects.filter(is_active=True))
    if not plans:
        defaults = [
            {
                "vehicle_type": "bike",
                "name": "Bike Captain",
                "icon": "🏍️",
                "base_fare": Decimal("30.00"),
                "per_km_rate": Decimal("8.00"),
                "commission_percentage": Decimal("20.00"),
                "surge_multiplier": Decimal("1.00"),
                "time_estimate": "2-4 min",
                "badge": "FASTEST & CHEAPEST",
                "description": "Beat the traffic with a verified Captain. Sanitized helmet provided.",
                "capacity": "1 person",
            },
            {
                "vehicle_type": "auto",
                "name": "Auto Rickshaw",
                "icon": "🛺",
                "base_fare": Decimal("40.00"),
                "per_km_rate": Decimal("12.00"),
                "commission_percentage": Decimal("15.00"),
                "surge_multiplier": Decimal("1.00"),
                "time_estimate": "3-5 min",
                "badge": "MOST POPULAR",
                "description": "Doorstep pickup at transparent fixed rates. No meter haggling.",
                "capacity": "3 persons",
            },
            {
                "vehicle_type": "cab",
                "name": "Cab Economy",
                "icon": "🚕",
                "base_fare": Decimal("70.00"),
                "per_km_rate": Decimal("18.00"),
                "commission_percentage": Decimal("25.00"),
                "surge_multiplier": Decimal("1.00"),
                "time_estimate": "5-7 min",
                "badge": "MAX COMFORT",
                "description": "Clean, air-conditioned compact cars for relaxed travel.",
                "capacity": "4 persons",
            },
        ]
        for d in defaults:
            PricingPlan.objects.get_or_create(vehicle_type=d["vehicle_type"], defaults=d)
        plans = list(PricingPlan.objects.filter(is_active=True))

    rates = {}
    for p in plans:
        rates[p.vehicle_type] = {
            "name": p.name,
            "icon": p.icon,
            "base_fare": p.base_fare,
            "per_km": p.per_km_rate,
            "commission": p.commission_percentage,
            "surge": p.surge_multiplier,
            "time": p.time_estimate,
            "badge": p.badge,
            "desc": p.description,
            "capacity": p.capacity,
            "plan_obj": p,
        }
    return rates


class DynamicFareRatesDict(dict):
    """Fallback proxy so existing FARE_RATES[...] lookups dynamically resolve to latest db pricing."""
    def __getitem__(self, key):
        rates = get_active_fare_rates()
        if key in rates:
            return rates[key]
        return super().__getitem__(key)

    def get(self, key, default=None):
        rates = get_active_fare_rates()
        return rates.get(key, default)

    def __iter__(self):
        return iter(get_active_fare_rates())

    def items(self):
        return get_active_fare_rates().items()

    def keys(self):
        return get_active_fare_rates().keys()

    def values(self):
        return get_active_fare_rates().values()


FARE_RATES = DynamicFareRatesDict()


POPULAR_LOCATIONS = {
    "Indiranagar 100ft Rd": {"name": "Indiranagar 100ft Road", "lat": 12.9784, "lng": 77.6408},
    "Koramangala 5th Block": {"name": "Koramangala 5th Block", "lat": 12.9352, "lng": 77.6245},
    "MG Road Metro Station": {"name": "MG Road Metro Station", "lat": 12.9756, "lng": 77.6066},
    "Whitefield ITPL": {"name": "Whitefield ITPL Tech Park", "lat": 12.9866, "lng": 77.7318},
    "Kempegowda Airport T1": {"name": "Kempegowda Airport T1", "lat": 13.1986, "lng": 77.7066},
    "Electronic City Phase 1": {"name": "Electronic City Phase 1", "lat": 12.8452, "lng": 77.6602},
    "HSR Layout Sector 1": {"name": "HSR Layout Sector 1", "lat": 12.9121, "lng": 77.6446},
    "Jayanagar 4th Block": {"name": "Jayanagar 4th Block", "lat": 12.9299, "lng": 77.5824},
    "Bellandur EcoSpace": {"name": "Bellandur EcoSpace", "lat": 12.9260, "lng": 77.6762},
    "Majestic Railway Station": {"name": "Majestic Railway Station", "lat": 12.9781, "lng": 77.5694},
}


def get_location_coordinates(name: str, is_destination: bool = False):
    cleaned = (name or "").lower().strip()
    for key, data in POPULAR_LOCATIONS.items():
        if key.lower() in cleaned or cleaned in key.lower() or data["name"].lower() in cleaned:
            return (data["lat"], data["lng"])
    # Deterministic fallback within Bengaluru city bounds
    seed = sum(ord(c) for c in cleaned) if cleaned else 42
    lat = 12.9100 + ((seed % 140) / 1000.0)
    lng = 77.5700 + (((seed * 7) % 150) / 1000.0)
    if is_destination and abs(lat - 12.9784) < 0.008:
        lat -= 0.035
        lng += 0.025
    return (round(lat, 5), round(lng, 5))


def calculate_distance(pickup: str, destination: str) -> Decimal:
    """Deterministically calculate a realistic city distance in km."""
    p_lat, p_lng = get_location_coordinates(pickup, is_destination=False)
    d_lat, d_lng = get_location_coordinates(destination, is_destination=True)
    
    # Approximate spherical distance in km
    dlat = (d_lat - p_lat) * 111.0
    dlng = (d_lng - p_lng) * 111.0 * 0.97
    approx_km = (dlat**2 + dlng**2) ** 0.5
    if approx_km < 1.5:
        approx_km = 2.5
    elif approx_km > 40.0:
        approx_km = 32.0
    return Decimal(str(round(approx_km, 1)))


# =========================================================
# HOME
# =========================================================

def home(request):
    popular_places = list(POPULAR_LOCATIONS.keys())
    return render(
        request,
        "booking/home.html",
        {
            "popular_places": popular_places,
            "popular_locations_json": json.dumps(POPULAR_LOCATIONS),
        }
    )


# =========================================================
# LOGIN & AUTHENTICATION
# =========================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or reverse("home")
    )

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect("home")

        messages.error(
            request,
            "Invalid username or password. Please try again."
        )

    return render(
        request,
        "booking/login.html",
        {
            "next": next_url
        }
    )


# =========================================================
# REGISTER
# =========================================================

def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if not username:
            messages.error(request, "Username is required.")
            return render(request, "booking/register.html")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists. Please pick another.")
            return render(request, "booking/register.html")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, "booking/register.html")

        if len(password1) < 6:
            messages.error(request, "Password must contain at least 6 characters.")
            return render(request, "booking/register.html")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )

        login(request, user)
        messages.success(request, f"Account created! Welcome to RideGo, {username}.")
        return redirect("home")

    return render(request, "booking/register.html")


# =========================================================
# LOGOUT
# =========================================================

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


# =========================================================
# SELECT RIDE
# =========================================================

def select_ride(request):
    if request.method == "POST":
        pickup = request.POST.get("pickup", "").strip()
        destination = request.POST.get("destination", "").strip()
        p_lat = request.POST.get("pickup_lat")
        p_lng = request.POST.get("pickup_lng")
        d_lat = request.POST.get("destination_lat")
        d_lng = request.POST.get("destination_lng")
    else:
        pickup = request.GET.get("pickup") or request.session.get("pickup", "")
        destination = request.GET.get("destination") or request.session.get("destination", "")
        p_lat = request.GET.get("pickup_lat")
        p_lng = request.GET.get("pickup_lng")
        d_lat = request.GET.get("destination_lat")
        d_lng = request.GET.get("destination_lng")

    if not pickup or not destination:
        messages.warning(request, "Please enter both pickup and destination locations.")
        return redirect("home")

    pickup_coords = (float(p_lat), float(p_lng)) if (p_lat and p_lng) else get_location_coordinates(pickup, is_destination=False)
    dest_coords = (float(d_lat), float(d_lng)) if (d_lat and d_lng) else get_location_coordinates(destination, is_destination=True)

    request.session["pickup"] = pickup
    request.session["destination"] = destination
    request.session["pickup_lat"] = pickup_coords[0]
    request.session["pickup_lng"] = pickup_coords[1]
    request.session["destination_lat"] = dest_coords[0]
    request.session["destination_lng"] = dest_coords[1]

    if not request.user.is_authenticated:
        messages.info(request, "Please log in to continue booking your ride.")
        return redirect(f"{reverse('login')}?next={reverse('select_ride')}")

    distance = calculate_distance(pickup, destination)
    request.session["distance"] = str(distance)

    fare_rates = get_active_fare_rates()
    rides = []
    for ride_key, meta in fare_rates.items():
        surge = meta.get("surge", Decimal("1.00"))
        fare = round((meta["base_fare"] + (distance * meta["per_km"])) * surge, 2)
        rides.append({
            "type": ride_key,
            "name": meta["name"],
            "icon": meta["icon"],
            "description": meta["desc"],
            "badge": meta["badge"],
            "time": meta["time"],
            "capacity": meta["capacity"],
            "fare": fare,
            "surge": surge,
        })

    return render(
        request,
        "booking/select_ride.html",
        {
            "pickup": pickup,
            "destination": destination,
            "pickup_lat": pickup_coords[0],
            "pickup_lng": pickup_coords[1],
            "destination_lat": dest_coords[0],
            "destination_lng": dest_coords[1],
            "distance": distance,
            "rides": rides,
        }
    )


# =========================================================
# BOOKING CONFIRMATION
# =========================================================

@login_required(login_url="login")
def booking_confirm(request):
    ride_type = request.POST.get("ride_type") or request.GET.get("ride_type") or "bike"
    fare_rates = get_active_fare_rates()

    if ride_type not in fare_rates:
        messages.error(request, "Invalid ride type selected.")
        return redirect("home")

    pickup = request.session.get("pickup")
    destination = request.session.get("destination")

    if not pickup or not destination:
        messages.warning(request, "Session expired. Please select your ride again.")
        return redirect("home")

    dist_str = request.session.get("distance")
    distance = Decimal(dist_str) if dist_str else calculate_distance(pickup, destination)

    p_lat = request.session.get("pickup_lat")
    p_lng = request.session.get("pickup_lng")
    d_lat = request.session.get("destination_lat")
    d_lng = request.session.get("destination_lng")

    meta = fare_rates[ride_type]
    surge = meta.get("surge", Decimal("1.00"))
    fare = round((meta["base_fare"] + (distance * meta["per_km"])) * surge, 2)

    return render(
        request,
        "booking/booking_confirm.html",
        {
            "ride_type": ride_type,
            "ride_name": meta["name"],
            "ride_icon": meta["icon"],
            "pickup": pickup,
            "destination": destination,
            "pickup_lat": p_lat,
            "pickup_lng": p_lng,
            "destination_lat": d_lat,
            "destination_lng": d_lng,
            "distance": distance,
            "base_fare": meta["base_fare"],
            "distance_fare": distance * meta["per_km"],
            "surge_multiplier": surge,
            "fare": fare,
            "time": meta["time"],
        }
    )


# =========================================================
# CREATE BOOKING
# =========================================================

@login_required(login_url="login")
def create_booking(request):
    if request.method != "POST":
        return redirect("home")

    ride_type = request.POST.get("ride_type")
    payment_method = request.POST.get("payment_method", "cash")
    pickup = request.session.get("pickup")
    destination = request.session.get("destination")
    fare_rates = get_active_fare_rates()

    if not pickup or not destination or ride_type not in fare_rates:
        messages.warning(request, "Invalid ride request details.")
        return redirect("home")

    dist_str = request.session.get("distance")
    distance = Decimal(dist_str) if dist_str else calculate_distance(pickup, destination)

    meta = fare_rates[ride_type]
    surge = meta.get("surge", Decimal("1.00"))
    fare = round((meta["base_fare"] + (distance * meta["per_km"])) * surge, 2)

    comm_rate = meta.get("commission", Decimal("20.00"))
    platform_profit = round(fare * (comm_rate / Decimal("100.00")), 2)
    captain_pay = fare - platform_profit

    p_lat = request.session.get("pickup_lat")
    p_lng = request.session.get("pickup_lng")
    d_lat = request.session.get("destination_lat")
    d_lng = request.session.get("destination_lng")

    pickup_lat, pickup_lng = (float(p_lat), float(p_lng)) if (p_lat and p_lng) else get_location_coordinates(pickup, is_destination=False)
    dest_lat, dest_lng = (float(d_lat), float(d_lng)) if (d_lat and d_lng) else get_location_coordinates(destination, is_destination=True)

    # Generate 4-digit security PIN
    otp_code = str(random.randint(1000, 9999))

    ride = Ride.objects.create(
        user=request.user,
        pickup=pickup,
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        destination=destination,
        destination_lat=dest_lat,
        destination_lng=dest_lng,
        ride_type=ride_type,
        distance=distance,
        estimated_fare=fare,
        surge_multiplier=surge,
        commission_rate=comm_rate,
        platform_profit=platform_profit,
        captain_earnings=captain_pay,
        payment_method=payment_method,
        payment_status="Pending",
        otp=otp_code,
        status="searching",
    )

    request.session["current_ride_id"] = ride.id
    messages.success(request, f"Ride #{ride.id} requested! Finding your nearest verified Captain...")

    return redirect("searching_driver", ride_id=ride.id)


# =========================================================
# SEARCHING DRIVER
# =========================================================

@login_required(login_url="login")
def searching_driver(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, user=request.user)

    if ride.status == "assigned":
        return redirect("driver_assigned", ride_id=ride.id)
    elif ride.status == "started":
        return redirect("start_ride", ride_id=ride.id)
    elif ride.status == "completed":
        return redirect("ride_detail", ride_id=ride.id)

    meta = FARE_RATES.get(ride.ride_type, FARE_RATES["bike"])

    return render(
        request,
        "booking/searching_driver.html",
        {
            "ride": ride,
            "meta": meta,
        }
    )


# =========================================================
# ASSIGN DRIVER (CAPTAIN MATCHING - APPROVED ONLY)
# =========================================================

@login_required(login_url="login")
def assign_driver(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, user=request.user)

    if ride.status in ["assigned", "started", "completed"]:
        return redirect("driver_assigned", ride_id=ride.id)

    # 1. Try finding available verified & permitted captain for this vehicle type
    driver = Driver.objects.filter(
        vehicle_type=ride.ride_type,
        is_verified=True,
        verification_status="approved",
        is_available=True
    ).first()

    # 2. If none currently free, reset availability of approved captains of that type so demo is smooth
    if not driver:
        Driver.objects.filter(
            vehicle_type=ride.ride_type,
            is_verified=True,
            verification_status="approved"
        ).update(is_available=True)
        driver = Driver.objects.filter(
            vehicle_type=ride.ride_type,
            is_verified=True,
            verification_status="approved"
        ).first()

    # 3. Fallback to any verified & permitted captain
    if not driver:
        driver = Driver.objects.filter(
            is_verified=True,
            verification_status="approved"
        ).first()

    if driver:
        ride.driver = driver
        ride.status = "assigned"
        ride.save()

        driver.is_available = False
        driver.save()

        messages.success(
            request,
            f"Verified Captain {driver.display_name} accepted your ride request!"
        )
    else:
        messages.warning(request, "No verified Captains currently online. Please check back shortly.")

    return redirect("driver_assigned", ride_id=ride.id)


# =========================================================
# DRIVER ASSIGNED
# =========================================================

@login_required(login_url="login")
def driver_assigned(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, user=request.user)

    if ride.status == "started":
        return redirect("start_ride", ride_id=ride.id)
    elif ride.status == "completed":
        return redirect("ride_detail", ride_id=ride.id)

    meta = FARE_RATES.get(ride.ride_type, FARE_RATES["bike"])

    return render(
        request,
        "booking/driver_assigned.html",
        {
            "ride": ride,
            "meta": meta,
        }
    )


# =========================================================
# START RIDE (LIVE TRIP SIMULATION)
# =========================================================

@login_required(login_url="login")
def start_ride(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, user=request.user)

    if ride.status == "assigned":
        ride.status = "started"
        ride.save()
        messages.info(request, "Ride started! Keep helmet/seatbelt fastened for safety.")

    meta = FARE_RATES.get(ride.ride_type, FARE_RATES["bike"])

    return render(
        request,
        "booking/ride_started.html",
        {
            "ride": ride,
            "meta": meta,
        }
    )


# =========================================================
# COMPLETE RIDE
# =========================================================

@login_required(login_url="login")
def complete_ride(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, user=request.user)

    ride.status = "completed"
    ride.payment_status = "Paid"
    ride.completed_at = timezone.now()
    if not ride.platform_profit or ride.platform_profit == 0:
        rate = ride.commission_rate or Decimal("20.00")
        ride.platform_profit = round(ride.estimated_fare * (rate / Decimal("100.00")), 2)
        ride.captain_earnings = ride.estimated_fare - ride.platform_profit
    ride.save()

    if ride.driver:
        ride.driver.is_available = True
        ride.driver.earnings += (ride.captain_earnings or (ride.estimated_fare * Decimal("0.80")))
        ride.driver.total_rides += 1
        ride.driver.save()

    messages.success(request, f"Ride #{ride.id} completed! Thank you for choosing RideGo.")

    meta = FARE_RATES.get(ride.ride_type, FARE_RATES["bike"])

    return render(
        request,
        "booking/ride_completed.html",
        {
            "ride": ride,
            "meta": meta,
        }
    )


# =========================================================
# CANCEL RIDE
# =========================================================

@login_required(login_url="login")
def cancel_ride(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, user=request.user)

    if ride.status in ["searching", "assigned"]:
        ride.status = "cancelled"
        ride.save()

        if ride.driver:
            ride.driver.is_available = True
            ride.driver.save()

        messages.info(request, f"Ride #{ride.id} was cancelled.")
    else:
        messages.warning(request, "Active or completed rides cannot be cancelled.")

    return redirect("my_rides")


# =========================================================
# RATE RIDE
# =========================================================

@login_required(login_url="login")
def rate_ride(request, ride_id):
    if request.method == "POST":
        ride = get_object_or_404(Ride, id=ride_id, user=request.user)
        rating_val = request.POST.get("rating")
        feedback_val = request.POST.get("feedback", "").strip()

        if rating_val and rating_val.isdigit():
            star = int(rating_val)
            if 1 <= star <= 5:
                ride.rating = star
        if feedback_val:
            ride.feedback = feedback_val

        ride.save()
        messages.success(request, "Thanks for your rating & feedback! Your review helps Captains.")

    return redirect("my_rides")


# =========================================================
# RIDE DETAIL (INVOICE & RECEIPT)
# =========================================================

@login_required(login_url="login")
def ride_detail(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, user=request.user)
    meta = FARE_RATES.get(ride.ride_type, FARE_RATES["bike"])

    return render(
        request,
        "booking/booking_detail.html",
        {
            "ride": ride,
            "meta": meta,
        }
    )


# =========================================================
# MY RIDES
# =========================================================

@login_required(login_url="login")
def my_rides(request):
    filter_type = request.GET.get("filter", "all")
    rides = Ride.objects.filter(user=request.user)

    if filter_type in ["completed", "assigned", "started", "cancelled"]:
        rides = rides.filter(status=filter_type)

    return render(
        request,
        "booking/my_rides.html",
        {
            "rides": rides,
            "current_filter": filter_type,
        }
    )


# =========================================================
# PROFILE
# =========================================================

@login_required(login_url="login")
def profile(request):
    user_rides = Ride.objects.filter(user=request.user)
    total_rides = user_rides.count()
    completed_rides = user_rides.filter(status="completed").count()

    from django.db.models import Sum
    total_spent = (
        user_rides.filter(status="completed").aggregate(Sum("estimated_fare"))["estimated_fare__sum"]
        or Decimal("0.00")
    )

    return render(
        request,
        "booking/profile.html",
        {
            "total_rides": total_rides,
            "completed_rides": completed_rides,
            "total_spent": total_spent,
            "wallet_balance": Decimal("350.00"),
        }
    )


# =========================================================
# CAPTAIN (RIDER/DRIVER) AUTHENTICATION & ONBOARDING
# =========================================================

def captain_register_view(request):
    """Allows new drivers to register, provide license/RC info, and submit for admin approval."""
    if request.user.is_authenticated and hasattr(request.user, "driver_profile"):
        driver = request.user.driver_profile
        if driver.is_permitted:
            return redirect("captain_dashboard")
        return redirect("captain_status")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")
        vehicle_type = request.POST.get("vehicle_type", "bike")
        vehicle_model = request.POST.get("vehicle_model", "").strip() or "Standard Model"
        vehicle_number = request.POST.get("vehicle_number", "").strip().upper()
        license_number = request.POST.get("license_number", "").strip().upper()
        rc_number = request.POST.get("rc_number", "").strip().upper()
        city = request.POST.get("city", "Bengaluru").strip()

        if not username or not password or not phone or not vehicle_number or not license_number:
            messages.error(request, "Please fill in all mandatory fields including vehicle and license details.")
            return render(request, "booking/captain_register.html")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists. Please choose a different username.")
            return render(request, "booking/captain_register.html")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=name.split()[0] if name else "",
            last_name=" ".join(name.split()[1:]) if name and len(name.split()) > 1 else ""
        )

        Driver.objects.create(
            user=user,
            name=name or username,
            phone=phone,
            vehicle_type=vehicle_type,
            vehicle_model=vehicle_model,
            vehicle_number=vehicle_number,
            license_number=license_number,
            rc_number=rc_number,
            city=city,
            verification_status="pending",
            is_verified=False,
            is_available=False,
            rating=Decimal("5.0"),
            total_rides=0,
            earnings=Decimal("0.00"),
            current_lat=12.9716,
            current_lng=77.5946,
        )

        login(request, user)
        messages.success(
            request,
            "Captain application submitted! Your legal documents are currently pending Admin verification."
        )
        return redirect("captain_status")

    return render(request, "booking/captain_register.html")


def captain_login_view(request):
    """Dedicated Captain Portal Login with Quick Test Login shortcuts."""
    if request.user.is_authenticated:
        if hasattr(request.user, "driver_profile"):
            driver = request.user.driver_profile
            if driver.is_permitted:
                return redirect("captain_dashboard")
            return redirect("captain_status")
        elif request.user.is_staff or request.user.is_superuser:
            return redirect("admin_portal")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if hasattr(user, "driver_profile"):
                driver = user.driver_profile
                if driver.is_permitted:
                    messages.success(request, f"Welcome back, Captain {driver.display_name}!")
                    return redirect("captain_dashboard")
                else:
                    messages.info(request, "Reviewing your Captain Permit status.")
                    return redirect("captain_status")
            elif user.is_staff or user.is_superuser:
                messages.success(request, f"Welcome Admin {user.username}!")
                return redirect("admin_portal")
            else:
                messages.warning(request, "You are logged in as a Rider. Apply below to become a Captain!")
                return redirect("captain_register")
        else:
            messages.error(request, "Invalid Captain username or password.")

    # Demo accounts for instant evaluation
    demo_captains = [
        {"username": "captain_rajesh", "type": "Bike (Permitted ✓)", "name": "Rajesh Kumar"},
        {"username": "captain_ramesh", "type": "Auto (Permitted ✓)", "name": "Ramesh Gowda"},
        {"username": "captain_deepak", "type": "Cab (Pending Verification ⏳)", "name": "Deepak Verma"},
        {"username": "captain_ajay", "type": "Auto (Rejected ❌)", "name": "Ajay Rathod"},
    ]

    return render(
        request,
        "booking/captain_login.html",
        {
            "demo_captains": demo_captains,
        }
    )


@login_required(login_url="captain_login")
def captain_status_view(request):
    """Displays Captain Application Verification status, inspection details, and permit badge."""
    driver = getattr(request.user, "driver_profile", None)
    if not driver:
        messages.info(request, "Please submit your Captain registration first.")
        return redirect("captain_register")

    # If captain was rejected and submits updated documents
    if request.method == "POST":
        license_number = request.POST.get("license_number", "").strip().upper()
        rc_number = request.POST.get("rc_number", "").strip().upper()
        vehicle_number = request.POST.get("vehicle_number", "").strip().upper()
        vehicle_model = request.POST.get("vehicle_model", "").strip()

        if license_number:
            driver.license_number = license_number
        if rc_number:
            driver.rc_number = rc_number
        if vehicle_number:
            driver.vehicle_number = vehicle_number
        if vehicle_model:
            driver.vehicle_model = vehicle_model

        driver.verification_status = "pending"
        driver.is_verified = False
        driver.rejection_reason = ""
        driver.save()
        messages.success(request, "Updated documents re-submitted for Admin verification!")
        return redirect("captain_status")

    return render(
        request,
        "booking/captain_status.html",
        {
            "driver": driver,
        }
    )


# =========================================================
# CAPTAIN LIVE COCKPIT & DASHBOARD
# =========================================================

@login_required(login_url="captain_login")
def captain_dashboard_view(request):
    """Full operational dashboard for approved Captains to receive rides, verify OTP, and navigate."""
    driver = getattr(request.user, "driver_profile", None)
    if not driver:
        return redirect("captain_register")

    if not driver.is_permitted:
        messages.warning(request, "Your permit is pending or not active. Please check your verification status.")
        return redirect("captain_status")

    # Check for ongoing active ride for this captain
    active_ride = Ride.objects.filter(
        driver=driver,
        status__in=["assigned", "started"]
    ).first()

    # Search for available ride requests matching captain's vehicle type
    incoming_rides = []
    if driver.is_available and not active_ride:
        incoming_rides = Ride.objects.filter(
            status="searching",
            ride_type=driver.vehicle_type
        ).order_by("-created_at")[:6]

    # Metrics
    today_completed = Ride.objects.filter(
        driver=driver,
        status="completed",
        completed_at__date=timezone.now().date()
    ).count()

    meta = FARE_RATES.get(driver.vehicle_type, FARE_RATES["bike"])

    return render(
        request,
        "booking/captain_dashboard.html",
        {
            "driver": driver,
            "active_ride": active_ride,
            "incoming_rides": incoming_rides,
            "today_completed": today_completed,
            "meta": meta,
        }
    )


@login_required(login_url="captain_login")
def captain_toggle_status_view(request):
    """Toggles Captain Online / Offline availability."""
    driver = getattr(request.user, "driver_profile", None)
    if not driver or not driver.is_permitted:
        return redirect("captain_status")

    driver.is_available = not driver.is_available
    driver.save()

    status_msg = "You are now ONLINE and ready to accept ride requests." if driver.is_available else "You are now OFFLINE. Take a well-deserved rest."
    messages.info(request, status_msg)
    return redirect("captain_dashboard")


@login_required(login_url="captain_login")
def captain_accept_ride_view(request, ride_id):
    """Captain explicitly accepts an incoming ride request."""
    driver = getattr(request.user, "driver_profile", None)
    if not driver or not driver.is_permitted:
        messages.error(request, "Only verified Captains can accept rides.")
        return redirect("captain_status")

    ride = get_object_or_404(Ride, id=ride_id)
    if ride.status != "searching":
        messages.warning(request, "This ride was already assigned or cancelled by another captain.")
        return redirect("captain_dashboard")

    ride.driver = driver
    ride.status = "assigned"
    ride.save()

    driver.is_available = False
    driver.save()

    messages.success(request, f"Ride #{ride.id} accepted! Navigate to pickup: {ride.pickup}")
    return redirect("captain_dashboard")


@login_required(login_url="captain_login")
def captain_arrived_pickup_view(request, ride_id):
    """Captain announces arrival at rider's pickup spot."""
    driver = getattr(request.user, "driver_profile", None)
    ride = get_object_or_404(Ride, id=ride_id, driver=driver)
    messages.success(request, f"Arrived at pickup location for Ride #{ride.id}. Ask passenger for 4-digit PIN.")
    return redirect("captain_dashboard")


@login_required(login_url="captain_login")
def captain_verify_otp_view(request, ride_id):
    """Authentic Rapido/Uber OTP verification: Captain enters the 4-digit PIN to start trip."""
    driver = getattr(request.user, "driver_profile", None)
    ride = get_object_or_404(Ride, id=ride_id, driver=driver)

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        if entered_otp == ride.otp:
            ride.status = "started"
            ride.save()
            messages.success(request, "✓ 4-Digit PIN Verified! Ride started safely.")
        else:
            messages.error(request, "❌ Incorrect OTP PIN! Please verify with rider.")

    return redirect("captain_dashboard")


@login_required(login_url="captain_login")
def captain_complete_ride_view(request, ride_id):
    """Captain completes the trip at destination, collects fare, and gets credited net payout."""
    driver = getattr(request.user, "driver_profile", None)
    ride = get_object_or_404(Ride, id=ride_id, driver=driver, status="started")

    ride.status = "completed"
    ride.payment_status = "Paid"
    ride.completed_at = timezone.now()

    if not ride.platform_profit or ride.platform_profit == Decimal("0.00"):
        comm = ride.commission_rate or Decimal("20.00")
        ride.platform_profit = round(ride.estimated_fare * (comm / Decimal("100.00")), 2)
        ride.captain_earnings = ride.estimated_fare - ride.platform_profit
    ride.save()

    payout = ride.captain_earnings or (ride.estimated_fare * Decimal("0.80"))
    driver.earnings += payout
    driver.total_rides += 1
    driver.is_available = True
    driver.save()

    messages.success(
        request,
        f"Ride #{ride.id} successfully completed! ₹{payout:.0f} credited to your earnings (Platform commission: ₹{ride.platform_profit:.0f})."
    )
    return redirect("captain_dashboard")


# =========================================================
# ADMIN VERIFICATION & PERMIT MANAGEMENT PORTAL
# =========================================================

def admin_portal_view(request):
    """High-end administrative cockpit for reviewing, verifying, permitting, or rejecting Captain applications."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "Admin permission required to access the Captain Permit Portal.")
        return render(request, "booking/admin_access_required.html")

    status_filter = request.GET.get("status", "all")
    captains_qs = Driver.objects.all().select_related("user").order_by("-created_at")

    if status_filter == "pending":
        captains = captains_qs.filter(verification_status="pending")
    elif status_filter == "approved":
        captains = captains_qs.filter(verification_status="approved")
    elif status_filter == "rejected":
        captains = captains_qs.filter(verification_status__in=["rejected", "suspended"])
    else:
        captains = captains_qs

    total_count = captains_qs.count()
    pending_count = captains_qs.filter(verification_status="pending").count()
    approved_count = captains_qs.filter(verification_status="approved").count()
    rejected_count = captains_qs.filter(verification_status__in=["rejected", "suspended"]).count()

    active_rides_count = Ride.objects.filter(status__in=["searching", "assigned", "started"]).count()

    return render(
        request,
        "booking/admin_captains_portal.html",
        {
            "captains": captains,
            "current_filter": status_filter,
            "total_count": total_count,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "active_rides_count": active_rides_count,
        }
    )


def admin_approve_captain_view(request, driver_id):
    """Admin verifies documents and grants commercial driving permit."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Unauthorized action.")
        return redirect("home")

    driver = get_object_or_404(Driver, id=driver_id)
    driver.verification_status = "approved"
    driver.is_verified = True
    driver.verified_at = timezone.now()
    driver.verified_by = request.user
    driver.rejection_reason = ""
    driver.is_available = True
    driver.save()

    messages.success(
        request,
        f"✓ Official Permit Granted! Captain {driver.display_name} ({driver.vehicle_number}) is verified and can now receive rides."
    )
    return redirect("admin_portal")


def admin_reject_captain_view(request, driver_id):
    """Admin rejects captain application with a structured reason."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Unauthorized action.")
        return redirect("home")

    driver = get_object_or_404(Driver, id=driver_id)
    reason = request.POST.get("rejection_reason", "").strip() or "Documents did not pass official safety and verification compliance."
    
    driver.verification_status = "rejected"
    driver.is_verified = False
    driver.rejection_reason = reason
    driver.is_available = False
    driver.save()

    messages.info(
        request,
        f"Application for Captain {driver.display_name} has been rejected. Reason logged: '{reason}'."
    )
    return redirect("admin_portal")


def admin_suspend_captain_view(request, driver_id):
    """Admin temporarily suspends or reinstates a captain's permit."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Unauthorized action.")
        return redirect("home")

    driver = get_object_or_404(Driver, id=driver_id)
    if driver.verification_status == "suspended":
        driver.verification_status = "approved"
        driver.is_verified = True
        driver.is_available = True
        messages.success(request, f"Permit reinstated for Captain {driver.display_name}.")
    else:
        driver.verification_status = "suspended"
        driver.is_verified = False
        driver.is_available = False
        messages.warning(request, f"Permit temporarily suspended for Captain {driver.display_name}.")
    driver.save()

    return redirect("admin_portal")


def admin_quick_login_view(request):
    """Convenient 1-click login as Admin Naveen for testing."""
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser("Naveen", "admin@ridego.com", "Admin123!")
    else:
        admin_user.set_password("Admin123!")
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

    login(request, admin_user)
    messages.success(request, f"Logged in as Administrator ({admin_user.username})!")
    next_url = request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("admin_business_dashboard")


# =========================================================
# REAL MAP API & LOCATIONS JSON ENDPOINT
# =========================================================

def api_nearby_captains_view(request):
    """Returns real coordinates of active permitted captains for interactive map rendering."""
    captains = Driver.objects.filter(
        is_verified=True,
        verification_status="approved",
        is_available=True
    )[:10]

    data = []
    for c in captains:
        data.append({
            "id": c.id,
            "name": c.display_name,
            "vehicle_type": c.vehicle_type,
            "vehicle_model": c.vehicle_model,
            "vehicle_number": c.vehicle_number,
            "lat": c.current_lat,
            "lng": c.current_lng,
            "rating": str(c.rating),
        })

    return JsonResponse({"captains": data, "count": len(data)})


# =========================================================
# ADMIN BUSINESS DASHBOARD & DYNAMIC PRICING CONTROL
# =========================================================

def admin_business_dashboard_view(request):
    """Executive Business Dashboard: Live ride metrics, platform profit, and dynamic fare management."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "Admin privileges required to access the Business Dashboard & Pricing Portal.")
        return render(request, "booking/admin_access_required.html")

    # Ensure dynamic pricing plans exist
    get_active_fare_rates()
    pricing_plans = PricingPlan.objects.all().order_by("id")

    # Filter rides ledger if requested
    status_filter = request.GET.get("status", "all")
    rides_qs = Ride.objects.all().select_related("user", "driver", "driver__user").order_by("-created_at")

    if status_filter == "completed":
        rides_list = rides_qs.filter(status="completed")
    elif status_filter == "active":
        rides_list = rides_qs.filter(status__in=["requested", "searching", "assigned", "started"])
    elif status_filter == "cancelled":
        rides_list = rides_qs.filter(status="cancelled")
    else:
        rides_list = rides_qs

    # Aggregated KPI Metrics
    total_rides = Ride.objects.count()
    completed_rides = Ride.objects.filter(status="completed").count()
    active_rides = Ride.objects.filter(status__in=["requested", "searching", "assigned", "started"]).count()
    cancelled_rides = Ride.objects.filter(status="cancelled").count()
    today_rides = Ride.objects.filter(created_at__date=timezone.now().date()).count()

    # Completed Rides Financials
    completed_qs = Ride.objects.filter(status="completed")
    gross_revenue = completed_qs.aggregate(total=Sum("estimated_fare"))["total"] or Decimal("0.00")
    total_profit = completed_qs.aggregate(total=Sum("platform_profit"))["total"] or Decimal("0.00")
    total_payout = completed_qs.aggregate(total=Sum("captain_earnings"))["total"] or Decimal("0.00")

    # Ensure sanity: if payout + profit hasn't been set on older records
    if total_payout == Decimal("0.00") and gross_revenue > 0:
        total_payout = gross_revenue - total_profit

    take_rate = round((total_profit / gross_revenue * 100), 1) if gross_revenue > 0 else Decimal("0.0")

    # Today's Financials
    today_completed = completed_qs.filter(completed_at__date=timezone.now().date())
    today_revenue = today_completed.aggregate(total=Sum("estimated_fare"))["total"] or Decimal("0.00")
    today_profit = today_completed.aggregate(total=Sum("platform_profit"))["total"] or Decimal("0.00")

    # Vehicle Type Performance breakdown
    vehicle_types = [
        {"key": "bike", "label": "Bike Captain", "icon": "🏍️", "color": "#f59e0b"},
        {"key": "auto", "label": "Auto Rickshaw", "icon": "🛺", "color": "#10b981"},
        {"key": "cab", "label": "Cab Economy", "icon": "🚗", "color": "#3b82f6"},
    ]

    vehicle_breakdown = []
    for vt in vehicle_types:
        v_key = vt["key"]
        v_rides = Ride.objects.filter(ride_type=v_key)
        v_comp = v_rides.filter(status="completed")
        v_rev = v_comp.aggregate(total=Sum("estimated_fare"))["total"] or Decimal("0.00")
        v_prof = v_comp.aggregate(total=Sum("platform_profit"))["total"] or Decimal("0.00")
        plan = pricing_plans.filter(vehicle_type=v_key).first()

        vehicle_breakdown.append({
            "key": v_key,
            "label": vt["label"],
            "icon": vt["icon"],
            "color": vt["color"],
            "plan": plan,
            "total_rides": v_rides.count(),
            "completed_rides": v_comp.count(),
            "revenue": v_rev,
            "profit": v_prof,
        })

    # Average profit per completed ride
    avg_profit_per_ride = round(total_profit / completed_rides, 2) if completed_rides > 0 else Decimal("0.00")

    context = {
        "pricing_plans": pricing_plans,
        "rides": rides_list[:35],
        "status_filter": status_filter,
        "total_rides": total_rides,
        "completed_rides": completed_rides,
        "active_rides": active_rides,
        "cancelled_rides": cancelled_rides,
        "today_rides": today_rides,
        "gross_revenue": gross_revenue,
        "total_profit": total_profit,
        "total_payout": total_payout,
        "take_rate": take_rate,
        "today_revenue": today_revenue,
        "today_profit": today_profit,
        "avg_profit_per_ride": avg_profit_per_ride,
        "vehicle_breakdown": vehicle_breakdown,
        "now": timezone.now(),
    }
    return render(request, "booking/admin_business_dashboard.html", context)


def admin_update_pricing_view(request):
    """Handles real-time price, commission, base-fare, and surge multiplier adjustments by Admin."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Unauthorized access.")
        return redirect("admin_business_dashboard")

    if request.method == "POST":
        action = request.POST.get("action", "update_single")

        if action == "quick_surge":
            preset = request.POST.get("preset")
            if preset == "rain":
                PricingPlan.objects.all().update(surge_multiplier=Decimal("1.40"))
                messages.success(request, "⛈️ Rainy Weather Surge activated (1.40x multiplier applied to all rides).")
            elif preset == "rush":
                PricingPlan.objects.all().update(surge_multiplier=Decimal("1.30"))
                messages.success(request, "🚦 Peak Hour Rush Surge activated (1.30x multiplier applied).")
            elif preset == "late_night":
                PricingPlan.objects.all().update(surge_multiplier=Decimal("1.20"))
                messages.success(request, "🌙 Late Night Surge activated (1.20x multiplier applied).")
            elif preset == "normal":
                PricingPlan.objects.all().update(surge_multiplier=Decimal("1.00"))
                messages.success(request, "☀️ Standard Normal Pricing restored (1.00x - No surge).")

        elif action == "update_single":
            plan_id = request.POST.get("plan_id")
            plan = get_object_or_404(PricingPlan, id=plan_id)

            try:
                base_fare = Decimal(request.POST.get("base_fare", str(plan.base_fare)).strip())
                per_km_rate = Decimal(request.POST.get("per_km_rate", str(plan.per_km_rate)).strip())
                commission = Decimal(request.POST.get("commission_percentage", str(plan.commission_percentage)).strip())
                surge = Decimal(request.POST.get("surge_multiplier", str(plan.surge_multiplier)).strip())
                is_active = request.POST.get("is_active") in ["on", "true", "True", "1"]

                plan.base_fare = max(Decimal("0.00"), base_fare)
                plan.per_km_rate = max(Decimal("1.00"), per_km_rate)
                plan.commission_percentage = min(Decimal("100.00"), max(Decimal("0.00"), commission))
                plan.surge_multiplier = max(Decimal("1.00"), surge)
                plan.is_active = is_active
                plan.save()

                messages.success(
                    request,
                    f"✓ Pricing for {plan.name} updated: Base ₹{plan.base_fare:.0f}, ₹{plan.per_km_rate:.0f}/km, {plan.commission_percentage:.0f}% profit cut, {plan.surge_multiplier:.2f}x surge."
                )
            except Exception as e:
                messages.error(request, f"Failed to update pricing: {str(e)}")

        elif action == "batch_update":
            plans = PricingPlan.objects.all()
            for plan in plans:
                b_fare_key = f"base_fare_{plan.id}"
                p_km_key = f"per_km_{plan.id}"
                comm_key = f"comm_{plan.id}"
                surge_key = f"surge_{plan.id}"

                if b_fare_key in request.POST:
                    try:
                        plan.base_fare = Decimal(request.POST.get(b_fare_key, str(plan.base_fare)).strip())
                        plan.per_km_rate = Decimal(request.POST.get(p_km_key, str(plan.per_km_rate)).strip())
                        plan.commission_percentage = Decimal(request.POST.get(comm_key, str(plan.commission_percentage)).strip())
                        plan.surge_multiplier = Decimal(request.POST.get(surge_key, str(plan.surge_multiplier)).strip())
                        plan.save()
                    except Exception:
                        pass
            messages.success(request, "✓ All dynamic pricing plans & profit rates successfully saved live!")

    return redirect("admin_business_dashboard")