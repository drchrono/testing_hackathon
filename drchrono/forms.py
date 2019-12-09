import social_django
from django import forms
from django.utils import timezone
from social_django.models import UserSocialAuth

from drchrono.endpoints import PatientEndpoint, AppointmentEndpoint
from drchrono.models import Visit


class CheckInForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    ssn = forms.CharField(max_length=150, required=False)

    def clean(self):
        try:
            oauth_provider = UserSocialAuth.objects.get(provider='drchrono')
            access_token = oauth_provider.extra_data['access_token']
        except social_django.models.UserSocialAuth.DoesNotExist:
            raise forms.ValidationError("We had a problem authenticating with the drchrono API.")

        self.appointments_client = AppointmentEndpoint(access_token)
        self.patient_client = PatientEndpoint(access_token)
        self.appointment_id = None
        self.patient_id = None

        # process the data in form.cleaned_data as required
        patient_found = False
        for patient in self.patient_client.list():
            first_name_match = patient.get('first_name') == self.cleaned_data.get('first_name')
            last_name_match = patient.get('last_name') == self.cleaned_data.get('last_name')
            ssn_match = patient.get('social_security_number') == self.cleaned_data.get('ssn')

            if all([first_name_match, last_name_match]):
                # we found a match
                patient_found = True
                self.patient_id = patient.get('id')

        if not patient_found:
            raise forms.ValidationError("Couldn't find a patient matching your name.")

        appointment_found = False
        today = timezone.now()
        today_str = today.strftime('%m-%d-%y')
        for appointment in self.appointments_client.list({'patient': self.patient_id}, start=today_str, end=today_str):
            # we found an appointment
            appointment_found = True
            self.appointment_id = appointment.get('id')

            # update appointment status to arrived
            self.appointments_client.update(self.appointment_id, {'status': 'Arrived'})

            # create the visit
            visit, created = Visit.objects.get_or_create(appointment_id=self.appointment_id, patient_id=self.patient_id)

            # if there is already a visit, and it is set to Arrived, they already checked in!
            if not created and visit.status == 'Arrived':
                raise forms.ValidationError("You already checked in for your appointment today.")

        if not appointment_found:
            raise forms.ValidationError("Couldn't find an appointment for you today.")


RACE_CHOICES = (
    ("", ""),
    ("indian", "American Indian or Alaska Native"),
    ("asian", "Asian"),
    ("black", "Black or African American"),
    ("hawaiian", "Native Hawaiian or Other Pacific Islander"),
    ("white", "White"),
    ("other", "Other Race"),
    ("declined", "Declined to specify"),
)

ETHNICITY_CHOICES = (
    ("blank", ""),
    ("hispanic", "Hispanic or Latino"),
    ("not_hispanic", "Not Hispanic or Latino"),
    ("declined", "Declined")
)


class DemographicForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    date_of_birth = forms.CharField(max_length=150, required=False)
    gender = forms.CharField(max_length=150, required=False)
    email = forms.CharField(max_length=150, required=False)
    race = forms.ChoiceField(choices=RACE_CHOICES, required=False)
    ethnicity = forms.ChoiceField(choices=ETHNICITY_CHOICES, required=False)


class TimerForm(forms.Form):
    appointment_id = forms.CharField(max_length=150, required=True)
