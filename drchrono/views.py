import time
from datetime import datetime, timedelta

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import TemplateView
from social_django.models import UserSocialAuth
from social_django.utils import load_strategy

from drchrono.endpoints import DoctorEndpoint, APIException, AppointmentEndpoint, PatientEndpoint
from drchrono.forms import CheckInForm, DemographicForm


class SetupView(TemplateView):
    """
    The beginning of the OAuth sign-in flow. Logs a user into the kiosk, and saves the token.
    """
    template_name = 'kiosk_setup.html'


class KioskEndView(TemplateView):
    """
    The beginning of the OAuth sign-in flow. Logs a user into the kiosk, and saves the token.
    """
    template_name = 'kiosk_finished.html'


class DemographicView(View):
    def get(self, request):
        oauth_provider = get_object_or_404(UserSocialAuth, provider='drchrono')
        access_token = oauth_provider.extra_data['access_token']
        patient_client = PatientEndpoint(access_token)
        patient = patient_client.fetch(request.GET.get('patient_id'))
        return render(request, 'demographics.html',
                      {'form': DemographicForm(initial=patient), 'patient_id': request.GET.get('patient_id')})

    def post(self, request):
        # create a form instance and populate it with data from the request:
        form = DemographicForm(request.POST)
        patient_id = request.POST.get('patient_id')

        # check whether it's valid:
        if form.is_valid():
            oauth_provider = get_object_or_404(UserSocialAuth, provider='drchrono')
            access_token = oauth_provider.extra_data['access_token']
            patient_client = PatientEndpoint(access_token)
            patient_client.update(patient_id, form.cleaned_data)
            return HttpResponseRedirect('/finished/')
        return render(request, 'demographics.html', {'form': form})


class CheckInView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'check_in.html', {'form': CheckInForm()})

    def post(self, request, *args, **kwargs):
        # create a form instance and populate it with data from the request:
        form = CheckInForm(request.POST)

        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            oauth_provider = get_object_or_404(UserSocialAuth, provider='drchrono')
            access_token = oauth_provider.extra_data['access_token']
            patient_client = PatientEndpoint(access_token)
            for patient in patient_client.list():
                first_name_match = patient.get('first_name') == form.cleaned_data.get('first_name')
                last_name_match = patient.get('last_name') == form.cleaned_data.get('last_name')
                ssn_match = patient.get('social_security_number') == form.cleaned_data.get('ssn')

                if all([first_name_match, last_name_match]) or ssn_match:
                    patient_id = patient.get('id')
                    appointments_client = AppointmentEndpoint(access_token)
                    for appointment in appointments_client.list({'patient': patient_id}, start='12-06-19',
                                                                end='12-06-19'):
                        appointment_id = appointment.get('id')
                        # update appointment status to arrived
                        appointments_client.update(appointment_id, {'status': 'Arrived'})

                        # redirect to demographics page with patient id as GET parameter
                        return HttpResponseRedirect(f'/demographics/?patient_id={patient_id}')
                # todo: add errors for non matching, appointment not found
        return render(request, 'check_in.html', {'form': form})


class DoctorWelcome(TemplateView):
    """
    The doctor can see what appointments they have today.
    """
    template_name = 'doctor_welcome.html'

    def get_token(self):
        """
        Social Auth module is configured to store our access tokens. This dark magic will fetch it for us if we've
        already signed in.
        """
        oauth_provider = get_object_or_404(UserSocialAuth, provider='drchrono')
        return oauth_provider.extra_data['access_token']

    def make_api_request(self):
        """
        Use the token we have stored in the DB to make an API request and get doctor details. If this succeeds, we've
        proved that the OAuth setup is working
        """
        # We can create an instance of an endpoint resource class, and use it to fetch details
        access_token = self.get_token()

        try:
            doctor = next(DoctorEndpoint(access_token).list())
        except APIException:
            # if this doesn't work we just return None
            return None

        # Grab the first doctor from the list, only one for this hackathon.
        return doctor

    def is_access_token_expired(self, access_token):
        oauth_provider = get_object_or_404(UserSocialAuth, provider='drchrono')
        difference = None
        if oauth_provider.extra_data and 'expires_in' in oauth_provider.extra_data:
            try:
                expires = int(oauth_provider.extra_data.get('expires_in'))
            except (ValueError, TypeError):
                return None

            now = datetime.utcnow()

            # Detect if expires is a timestamp
            if expires > time.mktime(now.timetuple()):
                # expires is a datetime, return the remaining difference
                difference = datetime.utcfromtimestamp(expires) - now
            else:
                # expires is the time to live seconds since creation,
                # check against auth_time if present, otherwise return
                # the value
                auth_time = oauth_provider.extra_data.get('auth_time')
                if auth_time:
                    reference = datetime.utcfromtimestamp(auth_time)
                    difference = (reference + timedelta(seconds=expires)) - now
                else:
                    difference = timedelta(seconds=expires)

        return difference and difference.total_seconds() <= oauth_provider.ACCESS_TOKEN_EXPIRED_THRESHOLD

    def get_context_data(self, **kwargs):
        """

        :param kwargs:
        :return:
        """
        kwargs = super(DoctorWelcome, self).get_context_data(**kwargs)
        # Hit the API using one of the endpoints just to prove that we can
        # If this works, then your oAuth setup is working correctly.
        doctor_details = self.make_api_request()
        kwargs['doctor'] = doctor_details

        oauth_provider = get_object_or_404(UserSocialAuth, provider='drchrono')
        if self.is_access_token_expired(oauth_provider.extra_data['access_token']):
            oauth_provider.refresh_token(load_strategy())

        access_token = oauth_provider.extra_data['access_token']
        appointments_client = AppointmentEndpoint(access_token)
        todays_appointments = list(appointments_client.list({}, start='12-06-19', end='12-06-19'))
        kwargs['appointments'] = todays_appointments

        arrived_appointments = [appointment for appointment in todays_appointments if
                                appointment.get('status') == 'Arrived']
        kwargs['arrived'] = arrived_appointments
        return kwargs
