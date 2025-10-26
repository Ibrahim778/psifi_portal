from django.db import models
from django.contrib.auth.models import User
from datetime import date, datetime
import json


def calculate_nights(arrival, departure):
    if arrival and departure:
        try:
            # Convert to date objects if not already
            if isinstance(arrival, str):
                arrival = datetime.strptime(arrival, "%Y-%m-%d").date()
            if isinstance(departure, str):
                departure = datetime.strptime(departure, "%Y-%m-%d").date()
            if arrival < departure:
                return (departure - arrival).days
        except Exception:
            pass
    return 1

class RegistrationLink(models.Model):
    user = models.CharField(max_length=128, unique=True) # Shouldn't have multiple registrations from the same head delegate
    cognito_link = models.URLField()

    def __str__(self):
        return f"{self.user or 'User'} / {self.cognito_link or 'Cognito Link'}"


class EventRegistration(models.Model):
    PAYMENT_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
    ]

    user = models.ForeignKey(User, related_name='registrations',
                             on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField()

    registration_type = models.CharField(max_length=32, blank=True, null=True)
    ca_name = models.CharField(max_length=128, blank=True, null=True)
    ca_code = models.CharField(max_length=32, blank=True, null=True)
    institution_name = models.CharField(max_length=128, blank=True, null=True)
    city = models.CharField(max_length=128, blank=True, null=True)
    team_name = models.CharField(max_length=128, blank=True, null=True)
    team_size = models.PositiveIntegerField(blank=True, null=True)
    preferences = models.JSONField(blank=True, null=True)
    registered_through_ca = models.BooleanField(default=False)

    # Payment info
    payment_status = models.CharField(
        max_length=10, choices=PAYMENT_CHOICES, default='Pending')
    delegation_fee = models.PositiveIntegerField(default=3500)
    event_fee_per_delegate = models.PositiveIntegerField(default=4000)
    accommodation_fee = models.PositiveIntegerField(
        default=0)  # Will be computed
    total_fee = models.PositiveIntegerField(default=0)
    payment_voucher = models.URLField(blank=True, null=True)

    payment_done = models.BooleanField(default=False)
    team_id = models.CharField(
        max_length=20, blank=True, null=True, unique=True)
    event1_fee = models.PositiveIntegerField(default=0)     # Will be computed

    def update_event_fee(self):
        self.event1_fee = (self.event_fee_per_delegate or 0) * \
            (self.team_size or 0)
        self.save(update_fields=['event1_fee'])
    print(event1_fee)

    # Chaperone info
    chaperone_name = models.CharField(max_length=128, blank=True, null=True)
    chaperone_cnic = models.CharField(max_length=32, blank=True, null=True)
    chaperone_mobile = models.CharField(max_length=32, blank=True, null=True)
    chaperone_email = models.EmailField(blank=True, null=True)
    chaperone_relationship = models.CharField(
        max_length=128, blank=True, null=True)
    chaperone_designation = models.CharField(
        max_length=128, blank=True, null=True)
    chaperone_image_url = models.URLField(blank=True, null=True)
    chaperone_accommodation = models.CharField(
        max_length=10, blank=True, null=True)

    undertaking = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    # Dynamic Early Bird cutoff: November 20 of current year
    EARLY_BIRD_EVENT_FEE = 4000
    REGULAR_EVENT_FEE = 4500
    REGULAR_DELEGATION_FEE = 3500
    EARLY_BIRD_DELEGATION_FEE = 0

    def is_early_bird(self):
        # Early Bird until Nov 20 of the current year, based on submission date
        sub_date = self.submitted_at.date() if self.submitted_at else date.today()
        cutoff = date(sub_date.year, 11, 20)
        return sub_date <= cutoff

    def calculate_accommodation_fee(self):
        total = 0
        for d in self.delegates.all():
            if str(d.accommodation).lower() == "yes":
                nights = d.number_of_nights or 1
                print("number of nights are")
                print(nights)
                total += 1500 * nights
        # If you want to add chaperone too, add logic here
        return total

    def update_event_fee(self):
        self.event1_fee = (self.event_fee_per_delegate or 0) * \
            (self.team_size or 0)

    def update_fees(self, save=True):
        from .models import EventRegistration  # for CA code queries

        print(self.event1_fee)
        self.update_event_fee()
        print(self.event1_fee)

        is_eb = self.is_early_bird()
        team_count = self.team_size or self.delegates.count()  # fallback to delegate count

        # Calculate CA discount
        ca_team_count = EventRegistration.objects.filter(
            ca_code=self.ca_code).count() if self.ca_code else 0
        ca_discount = self.ca_code and ca_team_count >= 5  # More than 4

        # --- Set event & delegation fee based on phase ---
        if is_eb:
            event_fee_per_delegate = 4000
            delegation_fee = 0
        else:
            event_fee_per_delegate = 4500
            delegation_fee = 3500

        # --- CA Discount (delegation fee = 0 for all CA teams if threshold reached) ---
        if ca_discount:
            delegation_fee = 0

            # Update all CA teams to have delegation_fee 0
            EventRegistration.objects.filter(
                ca_code=self.ca_code).update(delegation_fee=0)

        # --- Accommodation Fee ---
        accommodation_fee = self.calculate_accommodation_fee()

        # --- Calculate total ---
        event_fee = event_fee_per_delegate * team_count
        total = delegation_fee + event_fee + accommodation_fee

        # --- Assign for model ---
        self.event_fee_per_delegate = event_fee_per_delegate
        self.delegation_fee = delegation_fee
        self.accommodation_fee = accommodation_fee
        self.total_fee = total

        if save:
            super().save(update_fields=[
                "event_fee_per_delegate", "delegation_fee", "accommodation_fee", "total_fee"])

    def assign_team_id_if_needed(self, save=True):
        if self.payment_done and not self.team_id:
            from django.db.models.functions import Cast
            from django.db.models import IntegerField
            from django.db.models import F, Max
            qs = EventRegistration.objects.filter(
                team_id__startswith='LSS-')
            last_num = (
                qs.annotate(num=Cast(F('team_id')[4:], IntegerField()))
                .aggregate(Max('num'))['num__max'] or 0
            )
            next_num = last_num + 1
            self.team_id = f"LSS-{next_num:03d}"
            if save:
                self.save(update_fields=['team_id'])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_fees(save=False)  # don't double save

    def __str__(self):
        return f"{self.team_name or 'Team'} / {self.email}"

class EventDelegate(models.Model):
    registration = models.ForeignKey(
        EventRegistration, related_name='delegates', on_delete=models.CASCADE)
    number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=128, blank=True, null=True)
    age = models.PositiveSmallIntegerField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    cnic = models.CharField(max_length=32, blank=True, null=True)
    institution_name = models.CharField(max_length=128, blank=True, null=True)
    city = models.CharField(max_length=128, blank=True, null=True)
    education_level = models.CharField(max_length=64, blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    accommodation = models.CharField(
        max_length=10, blank=True, null=True)  # "Yes"/"No"
    date_of_arrival = models.DateField(blank=True, null=True)
    date_of_departure = models.DateField(blank=True, null=True)
    number_of_nights = models.PositiveIntegerField(default=1)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Whenever a delegate is saved, update fees for the registration
        if self.registration:
            self.registration.update_fees()

    def delete(self, *args, **kwargs):
        reg = self.registration
        super().delete(*args, **kwargs)
        if reg:
            reg.update_fees()

    def __str__(self):
        return f"Delegate {self.number} ({self.name}) / {self.registration.team_name}"

class CampusAmbassador(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=32, unique=True)
    password = models.CharField(max_length=128)  # Use hashed password
    email = models.EmailField(unique=True)
    institution = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # ...add any other CA-related fields...

    def __str__(self):
        return f"{self.name} ({self.code})"

# ...yall made a model to do exactly what I did and didn't even use it
# class FormState(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     form_name = models.CharField(max_length=100, default='psifi_registration')
#     form_data = models.JSONField(default=dict)
#     cognito_save_url = models.URLField(
#         blank=True, null=True)  # Store Cognito's save URL
#     last_updated = models.DateTimeField(auto_now=True)
#     is_submitted = models.BooleanField(default=False)

#     class Meta:
#         unique_together = ('user', 'form_name')

#     def __str__(self):
#         return f"{self.user.username} - {self.form_name}"
