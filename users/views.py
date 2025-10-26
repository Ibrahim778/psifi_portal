from django.shortcuts import render, get_object_or_404
from users.models import EventRegistration
from .forms import NamePasswordResetForm  # Adjust path as needed
from .models import CampusAmbassador, EventRegistration
from .models import EventRegistration
import re
from django.http import JsonResponse
from django.utils import timezone
import json
from .models import EventRegistration, EventDelegate
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from users.models import EventRegistration, EventDelegate
from django.db.models import Q
from .forms import CustomSignupForm  # You should create this!
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import CustomSignupForm
from django.contrib.auth.decorators import login_required
from django import forms
from .models import CampusAmbassador, calculate_nights
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.views.decorators.http import require_POST
import os
import requests
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import RegistrationLink
from .serializers import RegistrationLinkSerializer, UserSerializer, LinkSerializer
from django.utils.decorators import method_decorator

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None


def home_view(request):
    return render(request, 'home.html')


@never_cache
def signup_view(request):
    if request.method == 'POST':
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created for {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomSignupForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def dashboard_view(request):
    user_email = request.user.email

    # Check if this user is the head delegate of any registration
    reg = EventRegistration.objects.filter(
        email__iexact=user_email).first()

    # emails = _pull_sheet_emails()

    has_registration = False# user_email in emails

    # Debugging info
    print("Current user email:", repr(user_email))
    print("All registration emails:", list(
        EventRegistration.objects.values_list("email", flat=True)))
    print("Registration object:", reg)

    return render(request, "dashboard.html", {
        "has_registration": has_registration,
        "reg": reg,
    })


# 1. Embed Tally form (as an iframe in your template)

def register_page(request):
    # If user already has a registration, redirect to info page
    if EventRegistration.objects.filter(user=request.user).exists():
        return redirect('registration_info')
    # Your HTML with the iframe embed
    return render(request, 'embed_cognito.html')


# 2. Webhook to receive Tally responses and save to DB


@csrf_exempt
def tally_webhook(request):
    import re
    if request.method != "POST":
        return JsonResponse({"detail": "Only POST allowed"}, status=405)

    try:
        import json
        from django.utils import timezone
        data = json.loads(request.body)
        fields = data.get("data", {}).get("fields", [])

        def extract(key):
            for f in fields:
                if f.get("key") == key:
                    return f.get("value")
            return None

        def extract_choice_label(key):
            for f in fields:
                if f.get("key") == key and f.get("options"):
                    val = f.get("value")
                    if val and len(val) > 0:
                        for option in f["options"]:
                            if option["id"] == val[0]:
                                return option["text"]
            return None

        # Registration fields
        email = extract("question_lOV1Go_263842fb-8df7-4d40-8586-8d9347c1fe53")
        registration_type = extract_choice_label("question_LKYyZl")
        institution_name = extract("question_poW9b8")
        team_city = extract("question_14v5A1")
        ca_name = extract("question_471aDd")
        ca_code = extract("question_4714Rr")
        team_name = extract("question_MaYyek")
        team_size_label = extract_choice_label("question_JlDY1K")
        team_size = int(re.search(r"\d+", team_size_label).group()
                        ) if team_size_label else 0
        registered_through_ca = (
            registration_type == "Institution" and ca_code not in [None, ""])

        # Preferences (ranking)
        ranking_prefs = []
        for f in fields:
            if f.get("key") == "question_NXY1Pl":
                ranking_prefs = [option["text"] for option in f.get(
                    "options", []) if option["id"] in f.get("value", [])]

        # Prevent duplicate registration
        if EventRegistration.objects.filter(email=email, team_name=team_name).exists():
            return JsonResponse({"detail": "Already registered"}, status=409)
        User = get_user_model()

        reg = EventRegistration.objects.create(

            email=email,
            registration_type=registration_type,
            institution_name=institution_name,
            city=team_city,
            team_name=team_name,
            team_size=team_size,
            preferences={"ranking": ranking_prefs},
            submitted_at=timezone.now(),
        )

        # --- Delegate field keys for all 5 slots ---
        delegate_keys = [
            {
                "name": "question_y4vkXX",
                "age": "question_XoYy5L",
                "email": "question_8L85Nz",
                "phone": "question_08v5VB",
                "cnic": "question_zMJvEM",
                "institution_name": "question_59v5XZ",
                "city": "question_d0jVbd",
                "education_level": "question_YGYyjW",
                "image_url": "question_DpDyqN",
                "accommodation": "question_RoYNVP",
                "date_of_arrival": "question_rO04dp",
                "date_of_departure": "question_4716od",


            },
            {
                "name": "question_lOWZaN",
                "age": "question_RoYlW4",
                "email": "question_oRdQ9O",
                "phone": "question_GpDyeL",
                "cnic": "question_OXYyQY",
                "institution_name": "question_VPYypM",
                "city": "question_P9YyRB",
                "education_level": "question_ElDYqB",
                "image_url": "question_rOLWD2",
                "accommodation": "question_poW29B",
                "date_of_arrival": "question_jo0R7Y",
                "date_of_departure": "question_2AbWJg",
            },
            {
                "name": "question_47vdaA",
                "age": "question_joW2eJ",
                "email": "question_2Av5jD",
                "phone": "question_xDyBVv",
                "cnic": "question_ZOYy9e",
                "institution_name": "question_NXYyqO",
                "city": "question_qGWe5g",
                "education_level": "question_QRYyoX",
                "image_url": "question_9Zv5N5",
                "accommodation": "question_14va5l",
                "date_of_arrival": "question_xD0qPE",
                "date_of_departure": "question_ZOG7zA",
            },
            {
                "name": "question_y4vpqx",
                "age": "question_XoYvBY",
                "email": "question_8L8gpP",
                "phone": "question_08vgjj",
                "cnic": "question_zMJRQ0",
                "institution_name": "question_59vgqE",
                "city": "question_d0j42K",
                "education_level": "question_YGYKzJ",
                "image_url": "question_DpDEvZ",
                "accommodation": "question_MaYxyA",
                "date_of_arrival": "question_NX4jJN",
                "date_of_departure": "question_qGYrK8",
            },
            {
                "name": "question_lOW9lv",
                "age": "question_RoY6Bj",
                "email": "question_oRdaVx",
                "phone": "question_GpDjBk",
                "cnic": "question_OXYeBg",
                "institution_name": "question_VPYB1y",
                "city": "question_P9YWBe",
                "education_level": "question_ElDrbr",
                "image_url": "question_rOLbrR",
                "accommodation": "question_JlD4YR",
                "date_of_arrival": "question_QRxZJl",
                "date_of_departure": "question_9Z6kEK",
            },
        ]

        # --- Save all 5 delegates, null fields if missing ---
        for i in range(5):
            dkeys = delegate_keys[i]
            delegate_data = {
                "registration": reg,
                "number": i + 1,
            }
            arrival_val = extract(dkeys.get("date_of_arrival"))
            departure_val = extract(dkeys.get("date_of_departure"))

            number_of_nights = calculate_nights(arrival_val, departure_val)
            delegate_data["date_of_arrival"] = arrival_val
            delegate_data["date_of_departure"] = departure_val
            # <-- ADD THIS
            delegate_data["number_of_nights"] = number_of_nights
            for field, qkey in dkeys.items():
                if field in ["date_of_arrival", "date_of_departure", "number_of_nights"]:
                    continue
                val = extract(qkey)
                if field == "image_url" and val and isinstance(val, list):
                    delegate_data[field] = val[0]["url"]
                elif field in ["education_level", "accommodation"]:
                    delegate_data[field] = extract_choice_label(qkey)
                else:
                    delegate_data[field] = val
            cnic_val = delegate_data.get("cnic", "")
            # Only create if CNIC is present and non-empty
            if cnic_val and str(cnic_val).strip():
                EventDelegate.objects.create(**delegate_data)
        # --- Chaperone fields ---
        reg.chaperone_name = extract("question_er2X4o")
        reg.chaperone_cnic = extract("question_WRY7yQ")
        reg.chaperone_mobile = extract("question_a4EMVy")
        reg.chaperone_email = extract("question_6KvBo5")
        reg.chaperone_relationship = extract("question_7KvkGz")
        reg.chaperone_designation = extract("question_berJPE")
        chaperone_image_val = extract("question_ApDXZN")
        reg.chaperone_image_url = chaperone_image_val[0]['url'] if (
            chaperone_image_val and isinstance(chaperone_image_val, list)) else None
        reg.chaperone_accommodation = extract_choice_label("question_BpDRNY")

        # --- Undertaking ---
        undertaking_field = extract(
            "question_8L85qz_126d84d5-be88-4806-b7b3-4b1a4e0a1a7a")
        reg.undertaking = bool(undertaking_field)
        print("undertaking")

        # --- Compute fees and save ---
        reg.calculate_accommodation_fee()

        reg.update_fees()
        reg.save()

        print("Received Tally webhook and saved registration & delegates.")
        return JsonResponse({"detail": "Success"}, status=201)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"detail": str(e)}, status=500)


# 3. Show registration info to user
@login_required
def registration_info(request):
    reg = get_object_or_404(EventRegistration, user=request.user)
    delegates = reg.delegates.all()
    return render(request, 'registration_info.html', {'registration': reg, 'delegates': delegates})


@login_required
def register_page(request):
    # Optionally prevent multiple registrations here
    # ...
    return render(request, 'embed_cognito.html')


@login_required
@login_required
@login_required
def payment_voucher_view(request):
    registration = EventRegistration.objects.filter(
        email=request.user.email).first()
    if not registration:
        return redirect('register_page')

    # If payment voucher is pending, always update fees
    if not registration.payment_done:
        registration.update_fees(save=True)
        print("updates")
    else:

        registration.assign_team_id_if_needed(save=True)
        print("Assigned")

    context = {
        "registration": registration,
        # ... other context ...
    }
    return render(request, "payment_status.html", context)


def team_detail_view(request, pk):
    reg = get_object_or_404(EventRegistration, id=pk)
    delegates = EventDelegate.objects.filter(registration=reg)

    if not delegates.exists():
        delegates = EventDelegate.objects.filter(email=reg.email)
        # Or: SymposiumDelegate.objects.filter(team_name=reg.team_name)

    return render(request, 'team_detail.html', {
        'reg': reg,
        'delegates': delegates,
    })


def custom_logout_view(request):
    logout(request)  # Logs out the user
    return redirect('home')


def contact(request):

    return render(request, 'contact.html')


def categories(request):

    return render(request, 'categories.html')


def media(request):

    return render(request, 'lss.html')


def auto(request):

    return render(request, 'auto.html')


def life(request):

    return render(request, 'life.html')


def casignup(request):

    return render(request, 'ca_signup.html')


def aiml(request):

    return render(request, 'aiml.html')


def quantum(request):

    return render(request, 'quantum.html')


def schedule_view(request):
    return render(request, 'schedule.html')


def cadashboard(request):
    # 1. Check login/session
    ca_id = request.session.get('ca_id')
    if not ca_id:
        return redirect('ca_login')

    # 2. Get CA from db
    ca = get_object_or_404(CampusAmbassador, id=ca_id)

    # 3. Get teams with the same CA code (case-insensitive match)
    teams = EventRegistration.objects.filter(ca_code__iexact=ca.code)

    # 4. You can calculate stats here
    total_teams = teams.count()

    # 5. Pass everything to template
    return render(request, "ca_dashboard.html", {
        'ca': ca,
        'teams': teams,
        'total_teams': total_teams,

    })


def ca_login_view(request):
    error = None
    if request.method == "POST":
        code = request.POST.get('code')
        password = request.POST.get('password')
        try:
            ca = CampusAmbassador.objects.get(code=code)
            if password == ca.password:  # Simple string comparison
                request.session['ca_id'] = ca.id
                return redirect('ca')  # Change 'ca' as needed
            else:
                error = "Incorrect password."
        except CampusAmbassador.DoesNotExist:
            error = "Code not found."
    return render(request, "ca_login.html", {"error": error})


@csrf_exempt
def name_password_reset(request):
    if request.method == "POST":
        form = NamePasswordResetForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            new_password = form.cleaned_data['new_password1']

            try:
                user = User.objects.get(
                    username=username, first_name=first_name, last_name=last_name)
                user.set_password(new_password)
                user.save()
                messages.success(
                    request, "Password reset successful. You can now log in with your new password.")
                return redirect('login')  # Use your login url name
            except User.DoesNotExist:
                messages.error(request, "No user found with this information.")
    else:
        form = NamePasswordResetForm()
    return render(request, 'name_password_reset.html', {'form': form})


# def _pull_sheet_emails():
#     # Prefer env var; fallback to provided sheet ID
#     spreadsheet_id = os.environ.get(
#         'REGISTRATION_SHEETS_ID',
#         '1hzVqDWLQlHnqRs0xJHW8PIyLYY9vSOGYOr7EKJL2pQ8'
#     )
#     service_account_file = os.environ.get(
#         'GOOGLE_APPLICATION_CREDENTIALS',
#         os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'psifi-475008-e9cc54468e6b.json'))
#     )

#     scopes = [
#         'https://www.googleapis.com/auth/spreadsheets',
#         'https://www.googleapis.com/auth/drive'
#     ]

#     print('[Sheets] Using service account file:', service_account_file)
#     print('[Sheets] Spreadsheet ID:', spreadsheet_id)
#     creds = Credentials.from_service_account_file(
#         service_account_file, scopes=scopes)
#     client = gspread.authorize(creds)
#     sheet = client.open_by_key(spreadsheet_id).sheet1
    
#     # email_columns = []

#     # for (idx,col) in enumerate(sheet.row_values(1)):
#     #     print(f"idx: {idx} col: {col}")
#     #     if("Email" in col):
#     #         email_columns.append(idx + 1);

#     email_columns = [24, 35, 46, 57, 68, 80] # hardcoded it to speed up load times

#     emails = []
#     for i in email_columns:
#         emails += sheet.col_values(i)[1:]
    
#     return emails

# ---- Paymo PG Integration ----


def _append_payment_to_sheet(row_values):
    """Append a row to Google Sheets if gspread is available."""
    if gspread is None or Credentials is None:
        return False

    # Prefer env var; fallback to provided sheet ID
    spreadsheet_id = os.environ.get(
        'GOOGLE_SHEETS_ID',
        '1HwxsjxTXYtwkHEmEHuLL9WKI8dsUSWTJqGb55MJfzFk'
    )
    service_account_file = os.environ.get(
        'GOOGLE_APPLICATION_CREDENTIALS',
        os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(
            __file__)), 'cognitointegration-474313-0b8da5023027.json'))
    )

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    print('[Sheets] Using service account file:', service_account_file)
    print('[Sheets] Spreadsheet ID:', spreadsheet_id)
    creds = Credentials.from_service_account_file(
        service_account_file, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(spreadsheet_id).sheet1
    print('[Sheets] Appending row:', row_values)
    sheet.append_row(row_values, value_input_option='USER_ENTERED')
    print('[Sheets] Append successful')
    return True


def _extract_amount_from_entry(entry):
    """Safely extract total amount from Cognito entry payload without regex."""
    if not entry:
        return None

    # Prioritize TotalFee field from Cognito form
    for key in ['TotalFee']:
        if key in entry:
            try:
                val = entry[key]
                if isinstance(val, (int, float)):
                    print('[Amount] Found numeric at key', key, ':', val)
                    return int(val)
                # If it is a string number (no regex): use simple cast after stripping commas
                if isinstance(val, str):
                    cleaned = ''.join([c for c in val if c.isdigit()])
                    print('[Amount] Found string at key', key,
                          'raw=', val, 'cleaned=', cleaned)
                    return int(cleaned) if cleaned else None
            except Exception:
                pass

    # Fallback to other common patterns
    for key in ['total', 'Total', 'grand_total', 'GrandTotal', 'Grand_Total']:
        if key in entry:
            try:
                val = entry[key]
                if isinstance(val, (int, float)):
                    print('[Amount] Found numeric at key', key, ':', val)
                    return int(val)
                # If it is a string number (no regex): use simple cast after stripping commas
                if isinstance(val, str):
                    cleaned = ''.join([c for c in val if c.isdigit()])
                    print('[Amount] Found string at key', key,
                          'raw=', val, 'cleaned=', cleaned)
                    return int(cleaned) if cleaned else None
            except Exception:
                pass

    # Sometimes totals live in a nested object like calculations or summary
    for key in ['calculations', 'summary']:
        nested = entry.get(key)
        if isinstance(nested, dict):
            amount = _extract_amount_from_entry(nested)
            if amount is not None:
                return amount

    return None


def _calculate_total_from_entry(entry):
    """Compute total fee using form fields (Early Bird cutoff: Nov 20 current year).

    Pricing model (per person):
      - Early Bird: 2 Events = 7500, 3 Events = 8500
      - Regular:    2 Events = 8500, 3 Events = 9500

    Delegation fee:
      - Early Bird: 0 (waived)
      - Regular:    3500 (flat per team)

    Accommodation fee:
      - 1500 per night per delegate opting for accommodation (derived from Nights fields)
    """
    try:
        if not isinstance(entry, dict):
            return None, {}

        def to_int(val, default=0):
            if val is None:
                return default
            if isinstance(val, (int, float)):
                try:
                    return int(val)
                except Exception:
                    return default
            if isinstance(val, str):
                digits = "".join([c for c in val if c.isdigit()])
                return int(digits) if digits else default
            return default

        def get(obj, path):
            try:
                cur = obj
                for p in path.split('.'):
                    if isinstance(cur, dict) and p in cur:
                        cur = cur[p]
                    else:
                        return None
                return cur
            except Exception:
                return None

        # Normalize keys helper: build a lookup from simplified key -> original key
        def normalize_key(key: str) -> str:
            return ''.join(ch.lower() for ch in str(key) if ch.isalnum())

        def find_value_by_substrings(obj: dict, *needles: str):
            if not isinstance(obj, dict):
                return None
            norm_map = {normalize_key(k): k for k in obj.keys()}
            needles_norm = [normalize_key(n) for n in needles]
            for nk, orig in norm_map.items():
                if all(n in nk for n in needles_norm):
                    return obj.get(orig)
            return None

        # Determine submission time to classify phase
        submitted_raw = (
            get(entry, 'Entry.DateSubmitted') or entry.get('DateSubmitted') or entry.get('Submitted') or
            find_value_by_substrings(entry, 'date', 'submitted')
        )
        submitted_dt = None
        if isinstance(submitted_raw, str):
            try:
                submitted_dt = datetime.fromisoformat(
                    submitted_raw.replace('Z', '+00:00'))
            except Exception:
                try:
                    submitted_dt = datetime.strptime(
                        submitted_raw, '%Y-%m-%d %H:%M:%S')
                except Exception:
                    submitted_dt = None

        # Import datetime here to avoid local variable issue
        from datetime import datetime
        now = datetime.utcnow()
        cutoff = datetime(year=now.year, month=11, day=20,
                          hour=23, minute=59, second=59)
        # If submission date missing, assume now (so EB applies before cutoff)
        if submitted_dt is None:
            submitted_dt = now
        is_early_bird = bool(submitted_dt and submitted_dt <= cutoff)

        # Team size - count non-empty team member fields
        team_count = 0
        team_fields = ['Email', 'Email2', 'Email3', 'Email4']
        print('[DEBUG] Checking team fields:')
        for field in team_fields:
            val = entry.get(field)
            print(f'  {field}: {repr(val)}')
            if entry.get(field) and str(entry.get(field)).strip():
                team_count += 1
        print(f'[DEBUG] team_count: {team_count}')

        # Events selection - look for event choice fields
        print('[DEBUG] Checking event fields:')
        print(f'  Choice: {repr(entry.get("Choice"))}')
        print(f'  DracosSpine: {repr(entry.get("DracosSpine"))}')
        print(f'  HydrasLair: {repr(entry.get("HydrasLair"))}')
        print(f'  LadonsNest: {repr(entry.get("LadonsNest"))}')

        # Count selected events - check if each event field is present and truthy
        num_events = 0
        if entry.get('DracosSpine'):
            num_events += 1
            print('[DEBUG] DracosSpine selected')
        if entry.get('HydrasLair'):
            num_events += 1
            print('[DEBUG] HydrasLair selected')
        if entry.get('LadonsNest'):
            num_events += 1
            print('[DEBUG] LadonsNest selected')

        # If Choice field is used instead
        if num_events == 0:
            events_choice_raw = entry.get('Choice') or ''
            events_choice = str(events_choice_raw).lower()
            if 'dracos' in events_choice or 'spine' in events_choice:
                num_events += 1
            if 'hydras' in events_choice or 'lair' in events_choice:
                num_events += 1
            if 'ladons' in events_choice or 'nest' in events_choice:
                num_events += 1

        print(f'[DEBUG] num_events: {num_events}')

        # Per-person event price
        if is_early_bird:
            per_person = 7500 if num_events == 2 else 8500 if num_events == 3 else 0
        else:
            per_person = 8500 if num_events == 2 else 9500 if num_events == 3 else 0

        events_price = per_person * team_count

        # Calculate nights from arrival/departure dates
        total_nights = 0
        print('[DEBUG] Checking accommodation dates:')
        try:
            arrival_fields = ['DateOfArrival',
                              'DateOfArrival2', 'DateOfArrival3']
            departure_fields = ['DateOfDeparture',
                                'DateOfDeparture2', 'DateOfDeparture3']

            for i, arrival_field in enumerate(arrival_fields):
                arrival = entry.get(arrival_field)
                departure = entry.get(
                    departure_fields[i] if i < len(departure_fields) else '')
                print(
                    f'  {arrival_field}: {repr(arrival)}, {departure_fields[i]}: {repr(departure)}')

                if arrival and departure:
                    try:
                        from datetime import datetime
                        arr_dt = datetime.strptime(
                            str(arrival), '%Y-%m-%d').date()
                        dep_dt = datetime.strptime(
                            str(departure), '%Y-%m-%d').date()
                        nights = (dep_dt - arr_dt).days
                        total_nights += max(1, nights)  # At least 1 night
                        print(f'    -> {nights} nights')
                    except Exception as e:
                        print(f'    -> Error parsing dates: {e}')
                        total_nights += 1  # Default to 1 night if parsing fails
        except Exception as e:
            print(f'[DEBUG] Accommodation error: {e}')
            pass
        print(f'[DEBUG] total_nights: {total_nights}')

        per_night = 1500
        accommodation_fee = total_nights * per_night

        # Delegation fee is flat 3500 (per team)
        delegation_fee = 3500 if is_early_bird else 4000

        total = events_price + accommodation_fee + delegation_fee

        debug = {
            # 1=EB, 2=Regular (numeric as requested)
            'phase': 1 if is_early_bird else 2,
            'per_person': per_person,
            'team_count': team_count,
            'num_events': num_events,
            'events_price': events_price,
            'total_nights': total_nights,
            'per_night': per_night,
            'accommodation_fee': accommodation_fee,
            'delegation_fee': delegation_fee,
            'total': total,
        }

        return total, debug
    except Exception as e:
        print(f'[DEBUG] Exception in _calculate_total_from_entry: {e}')
        import traceback
        traceback.print_exc()
        return None, {}


@csrf_exempt
@require_POST
def create_payment(request):
    """Create a Paymo transaction from Cognito afterSubmit payload and return redirect URL."""
    try:
        body = json.loads(request.body or '{}')
    except Exception:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)

    # Cognito message structures vary; support a few keys
    entry = body.get('entry') or body.get(
        'data') or body.get('payload') or body

    # DEBUG: Log the full structure to understand what we're receiving
    print('[DEBUG] Full request body keys:', sorted(list(body.keys())))
    print('[DEBUG] Entry type:', type(entry))
    if isinstance(entry, dict):
        print('[DEBUG] Entry keys (first 20):',
              sorted(list(entry.keys()))[:20])

    # DON'T extract nested Entry - it only contains metadata, not form field data
    # The nested Entry only has metadata like ['Action', 'AdminLink', 'DateCreated', etc.]
    # The actual form field data should be in the original entry object
    original_entry = entry

    # Look for form fields in the original entry
    # Check if we have the expected form fields
    has_form_fields = any(key in original_entry for key in [
        'Email', 'Email2', 'Email3', 'TeamSize', 'Choice',
        'DracosSpine', 'HydrasLair', 'LadonsNest'
    ])

    if not has_form_fields:
        print('[DEBUG] No form fields found in original entry')
        # The form data might be in a different structure
        # Let's check if there's a nested structure with the actual form data
        for key, value in original_entry.items():
            if isinstance(value, dict) and len(value) > 5:  # Likely contains form data
                print(f'[DEBUG] Checking nested object at key "{key}" with keys:', sorted(
                    list(value.keys()))[:10])
                # Check if this nested object has form fields
                if any(field in value for field in ['Email', 'Email2', 'TeamSize', 'Choice']):
                    print(
                        f'[DEBUG] Found form fields in nested object at key "{key}"')
                    entry = value
                    break

    try:
        if isinstance(entry, dict):
            print('[Entry] keys:', sorted(list(entry.keys()))[:50])
    except Exception:
        pass

    # Support multiple casings/keys from Cognito entry
    email = (
        entry.get('email') or entry.get('Email') or body.get(
            'email') or body.get('Email')
    )
    team_name = (
        entry.get('team_name') or entry.get('teamName') or entry.get(
            'TeamName') or body.get('team_name') or body.get('TeamName')
    )

    print(
        f'[DEBUG] Extracted email: {repr(email)}, team_name: {repr(team_name)}')

    # Prefer server-side computed total using entry fields; fallback to embedded totals
    amount, fee_debug = _calculate_total_from_entry(entry)

    # If amount is still 0 or None, try to find it in the entry data
    if not amount or amount <= 0:
        print('[DEBUG] No amount calculated, looking for TotalFee in entry')
        amount = _extract_amount_from_entry(entry)
        if amount:
            print(f'[DEBUG] Found amount from entry extraction: {amount}')

    # Always print Fee block
    try:
        print('[Fee] phase(1=EB,2=Regular):', fee_debug.get('phase', 0))
        print('[Fee] per_person:', fee_debug.get('per_person', 0))
        print('[Fee] team_count:', fee_debug.get('team_count', 0))
        print('[Fee] num_events:', fee_debug.get('num_events', 0))
        print('[Fee] events_price:', fee_debug.get('events_price', 0))
        print('[Fee] total_nights:', fee_debug.get('total_nights', 0))
        print('[Fee] per_night:', fee_debug.get('per_night', 0))
        print('[Fee] accommodation_fee:',
              fee_debug.get('accommodation_fee', 0))
        print('[Fee] delegation_fee:', fee_debug.get('delegation_fee', 0))
        print('[Fee] total:', fee_debug.get('total', amount or 0))
    except Exception:
        pass

    # Find an existing registration by email+team_name if possible
    reg = None
    if email and team_name:
        reg = EventRegistration.objects.filter(
            email__iexact=email, team_name__iexact=team_name).first()
    elif email:
        reg = EventRegistration.objects.filter(
            email__iexact=email).order_by('-submitted_at').first()

    if reg and (amount is None or amount <= 0):
        # Ensure fees are up to date
        print('[CreatePayment] Falling back to registration total for',
              email, team_name)
        reg.update_fees(save=True)
        amount = reg.total_fee or 0
        print('[CreatePayment] Registration total:', amount)

    if not isinstance(amount, int) or amount <= 0:
        print(
            f'[CreatePayment] Invalid amount: {amount} (type: {type(amount)})')
        return JsonResponse({'detail': f'Missing or invalid amount: {amount}', 'debug': fee_debug}, status=400)

    paymo_base = os.environ.get(
        'PAYMO_BASE_URL', 'https://dev-dot-cardpay-1.el.r.appspot.com')
    paymo_api_key = os.environ.get('PAYMO_API_KEY')
    paymo_api_secret = os.environ.get('PAYMO_API_SECRET')

    if not paymo_api_key or not paymo_api_secret:
        print('[CreatePayment] Missing Paymo credentials in environment')
        return JsonResponse({'detail': 'Server misconfigured: missing Paymo credentials'}, status=500)

    # Callback URL where Paymo will POST completion status
    callback_url = request.build_absolute_uri('/api/paymo/callback/')

    try:
        print('[CreatePayment] Calling Paymo at',
              f"{paymo_base}/api/v1/paymo-pg/create-transaction")
        resp = requests.post(
            f"{paymo_base}/api/v1/paymo-pg/create-transaction",
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': paymo_api_key,
                'X-API-Secret': paymo_api_secret,
            },
            json={
                'amount': amount,
                'checkout_url': callback_url,
            },
            timeout=20,
        )
        print('[CreatePayment] Paymo response status:', resp.status_code)
        if resp.status_code >= 400:
            print('[CreatePayment] Paymo error body:', resp.text)
            return JsonResponse({'detail': 'Paymo error', 'status': resp.status_code, 'body': resp.text}, status=502)
        data = resp.json()
        print('[CreatePayment] Paymo response JSON:', data)
        # Try multiple shapes: flat, nested under 'data', alternative keys
        redirect_url = (
            data.get('redirect_url') or
            data.get('redirect') or
            data.get('redirectUrl') or
            data.get('payment_url') or
            (data.get('data', {}) if isinstance(data.get('data'), dict) else {}).get('redirect_url') or
            (data.get('data', {}) if isinstance(data.get('data'), dict) else {}).get('redirect') or
            (data.get('data', {}) if isinstance(
                data.get('data'), dict) else {}).get('redirectUrl')
        )
        if not redirect_url:
            print('[CreatePayment] Missing redirect_url in Paymo response')
            return JsonResponse({'detail': 'Missing redirect_url from Paymo', 'gateway_raw': data}, status=502)

        # Save payment URL to DB for later display
        if reg:
            reg.payment_voucher = redirect_url
            reg.save(update_fields=['payment_voucher'])
            print('[CreatePayment] Saved payment_voucher for registration id:', reg.id)

        # Append to Google Sheets (best-effort)
        try:
            timestamp = datetime.utcnow().isoformat()
            row = [
                email or '',
                team_name or '',
                str(amount),
                redirect_url,
                timestamp,
            ]
            _append_payment_to_sheet(row)
        except Exception:
            import traceback
            print('[Sheets] Append failed')
            traceback.print_exc()

        return JsonResponse({'payment_url': redirect_url})
    except requests.RequestException as e:
        print('[CreatePayment] Network error to Paymo:', str(e))
        return JsonResponse({'detail': 'Network error to Paymo', 'error': str(e)}, status=502)

@csrf_exempt
@require_POST
def paymo_callback(request):
    """Receive Paymo checkout callback with transaction status and update registration."""
    try:
        payload = json.loads(request.body or '{}')
    except Exception:
        payload = {}

    # Expected fields are not specified; try common ones
    status_value = payload.get('status') or payload.get('payment_status')
    email = payload.get('email')
    team_name = payload.get('team_name') or payload.get('teamName')
    redirect_url = payload.get('redirect_url')

    reg = None
    if email and team_name:
        reg = EventRegistration.objects.filter(
            email__iexact=email, team_name__iexact=team_name).first()
    elif email:
        reg = EventRegistration.objects.filter(
            email__iexact=email).order_by('-submitted_at').first()

    if reg:
        if status_value and str(status_value).lower() in ['paid', 'success', 'completed']:
            reg.payment_status = 'Paid'
            reg.payment_done = True
            reg.assign_team_id_if_needed(save=False)
        elif status_value and str(status_value).lower() in ['failed', 'error', 'declined']:
            reg.payment_status = 'Failed'
        if redirect_url:
            reg.payment_voucher = redirect_url
        reg.save()

    return JsonResponse({'ok': True})

# THESE ARE INSECURE we should fix
# Endpoint for client side js to read and write to cognito link db.

class CongitoLinkStore(APIView):
    authentication_classes = []  # disables all authentication (needed for csrf)

    def post(self, request):
        userSerializer = UserSerializer(data=request.data)
        linkSerializer = LinkSerializer(data=request.data)

        if not linkSerializer.is_valid():
            return Response(serializer.errors, status=400) # Malformed input

        if userSerializer.is_valid(): # try and find an already existing registration with this email, we will update it
            try:
                registration = RegistrationLink.objects.get(user=userSerializer.validated_data['user'])
                registration.cognito_link = linkSerializer.validated_data['cognito_link']
                registration.save()
                return Response({"message": "Updated"}, status=201)

            except:
                pass # just fall through
            
            
        serializer = RegistrationLinkSerializer(data=request.data) # We use this one specifically so it can validate input
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Saved."}, status=201)
        
        return Response(serializer.errors, status=400)

class CognitoLinkGet(APIView):
    authentication_classes = []  # disables all authentication (needed for csrf)

    def post(self, request): # Client will send a post request with the email
        serializer = UserSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                reglink = RegistrationLink.objects.get(user=serializer.validated_data['user'])
            except:
                return Response({"error": "Registration link not found."}, status=404)
            
            return Response(RegistrationLinkSerializer(reglink).data, status=200)

        return Response(serializer.errors, status=400)


# ---- Debug utilities ----


@csrf_exempt
@require_POST
def debug_sheets_append(request):
    """Append a test row to Google Sheets to verify credentials and sharing."""
    try:
        body = json.loads(request.body or '{}')
    except Exception:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)

    email = body.get('email') or ''
    team_name = body.get('team_name') or ''
    amount = body.get('amount') or ''
    payment_url = body.get('payment_url') or 'https://example.com/test'
    timestamp = datetime.utcnow().isoformat()

    row = [str(email), str(team_name), str(
        amount), str(payment_url), timestamp]
    try:
        print('[Sheets][Debug] Attempting append of row:', row)
        ok = _append_payment_to_sheet(row)
        return JsonResponse({'ok': bool(ok), 'row': row})
    except Exception as e:
        import traceback
        print('[Sheets][Debug] Append failed:', str(e))
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
