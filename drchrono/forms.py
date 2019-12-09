from django import forms
from django.utils import timezone
from social_django.models import UserSocialAuth

from drchrono.endpoints import PatientEndpoint, AppointmentEndpoint
from drchrono.models import Visit


class CheckInForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)

    def clean(self):
        try:
            oauth_provider = UserSocialAuth.objects.get(provider='drchrono')
            access_token = oauth_provider.extra_data['access_token']
        except UserSocialAuth.DoesNotExist:
            raise forms.ValidationError("We had a problem authenticating with the drchrono API.")

        full_name = f"{self.cleaned_data.get('first_name')} {self.cleaned_data.get('last_name')}"

        appointments_client = AppointmentEndpoint(access_token)
        patient_client = PatientEndpoint(access_token)
        self.cleaned_data['appointment_id'] = None
        self.cleaned_data['patient_id'] = None

        # get a list of patients, make a list of their full names to search through
        patients = list(patient_client.list())
        patients_full_names = [f"{patient.get('first_name')} {patient.get('last_name')}" for patient in
                               list(patient_client.list())]
        patient_found = full_name in patients_full_names
        if not patient_found:
            raise forms.ValidationError("Couldn't find a patient matching your name.")

        patient = patients[patients_full_names.index(full_name)]
        self.cleaned_data['patient_id'] = patient.get('id')

        # okay, we found them. do they have an appt. ?
        today = timezone.now()
        today_str = today.strftime('%m-%d-%y')
        appointments = list(
            appointments_client.list({'patient': self.cleaned_data.get('patient_id')}, start=today_str, end=today_str))
        patient_has_appointment_today = len(appointments) > 0
        if not patient_has_appointment_today:
            raise forms.ValidationError("Couldn't find an appointment for you today.")

        # if they have any appointments set their status to Arrived
        for appointment in appointments:
            self.cleaned_data['appointment_id'] = appointment.get('id')
            appointments_client.update(self.cleaned_data['appointment_id'], {'status': 'Arrived'})

            # create a Visit object
            visit, created = Visit.objects.get_or_create(appointment_id=self.cleaned_data['appointment_id'],
                                                         patient_id=self.cleaned_data['patient_id'])

            # if there was already a Visit object and it is set to Arrived, they already checked in!
            if not created and visit.status == 'Arrived':
                raise forms.ValidationError("You already checked in for your appointment today.")



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
