import math
import time
from datetime import datetime, timedelta

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from social_django.models import UserSocialAuth
from social_django.utils import load_strategy

from drchrono.endpoints import DoctorEndpoint, APIException, AppointmentEndpoint, PatientEndpoint
from drchrono.forms import CheckInForm, DemographicForm, TimerForm
from drchrono.models import Visit


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

        if form.is_valid():
            # update appointment status to arrived on api
            form.appointments_client.update(form.appointment_id, {'status': 'Arrived'})

            # locally set status to arrived, and arrival_time to now
            visit = Visit.objects.get(appointment_id=form.appointment_id,
                                      patient_id=form.patient_id)
            visit.arrival_time = timezone.now()
            visit.status = 'Arrived'
            visit.save()
            return HttpResponseRedirect(f'/demographics/?patient_id={form.patient_id}')
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

            now = timezone.now()

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
                    reference = timezone.make_aware(datetime.utcfromtimestamp(auth_time))
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

        patient_client = PatientEndpoint(access_token)
        patients = list(patient_client.list())

        appointments_client = AppointmentEndpoint(access_token)
        todays_appointments = list(appointments_client.list({}, start='12-06-19', end='12-06-19'))

        for appointment in todays_appointments:
            patient = [patient for patient in patients if patient.get('id') == appointment.get('patient')][0]
            appointment['first_name'] = patient.get('first_name')
            appointment['last_name'] = patient.get('last_name')

        kwargs['appointments'] = todays_appointments

        visits = Visit.objects.filter(status='Arrived', arrival_time__isnull=False, start_time__isnull=True).all()
        for visit in visits:
            visit.wait_since_arrived = visit.get_wait_duration().seconds
            patient = [patient for patient in patients if patient.get('id') == visit.patient_id][0]
            visit.first_name = patient.get('first_name')
            visit.last_name = patient.get('last_name')
        kwargs['arrived'] = visits

        current_appointment = Visit.objects.filter(status='In Session', arrival_time__isnull=False,
                                                   start_time__isnull=False).first()
        if current_appointment:
            kwargs['current_appointment'] = current_appointment
            current_appointment.visit_duration = current_appointment.get_visit_duration().seconds
            patient = [patient for patient in patients if patient.get('id') == current_appointment.patient_id][0]
            current_appointment.first_name = patient.get('first_name')
            current_appointment.last_name = patient.get('last_name')
            current_appointment.date_of_birth = patient.get('date_of_birth')
            current_appointment.date_of_last_appointment = patient.get('date_of_last_appointment')
            current_appointment.race = patient.get('race')
            current_appointment.gender = patient.get('gender')
            current_appointment.ethnicity = patient.get('ethnicity')

        past_visits = Visit.objects.filter(status="Finished", arrival_time__isnull=False,
                                           start_time__isnull=False).all()

        if len(past_visits) > 0:
            avg_wait_time = sum([(visit.start_time - visit.arrival_time).seconds for visit in past_visits]) / len(
                past_visits)
            kwargs['avg_wait_duration'] = math.ceil(avg_wait_time)

            avg_visit_duration = sum([(visit.end_time - visit.start_time).seconds for visit in past_visits]) / len(
                past_visits)
            kwargs['avg_visit_duration'] = math.ceil(avg_visit_duration)
        else:
            kwargs['avg_wait_duration'] = "You have no arrivals!"
            kwargs['avg_visit_duration'] = "You have no visits!"
        return kwargs


class VisitTimerView(View):
    def toggle_timer(self, appointment_id):
        visit = Visit.objects.get(appointment_id=appointment_id)

        if visit.status == "Arrived":
            visit.start_time = timezone.now()
            visit.status = "In Session"
            visit.save()
        elif visit.status == "In Session":
            visit.end_time = timezone.now()
            visit.status = "Finished"
            visit.save()
        else:
            raise Exception(f"{visit} has an invalid status of: {visit.status} {type(visit.status)}")

    def post(self, request):
        form = TimerForm(request.POST)
        if form.is_valid():
            self.toggle_timer(appointment_id=form.cleaned_data.get('appointment_id'))
        return HttpResponseRedirect(f'/welcome/')
