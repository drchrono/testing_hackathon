import time

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from social_django.models import UserSocialAuth

from drchrono.endpoints import DoctorEndpoint
from drchrono.models import Visit
from drchrono.views import DoctorWelcome, VisitTimerView, CheckInView, DemographicView


class SetupViewTests(TestCase):
    def test_kiosk_setup(self):
        response = self.client.get(reverse('setup'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'<a href="/login/drchrono/">\n      Set up your Check-in kiosk by logging into drchrono!\n    </a>\n',
            response.content)


class DoctorWelcomeTests(TestCase):
    def setUp(self):
        self.doctor_endpoint = DoctorEndpoint()
        self.doctor_welcome = DoctorWelcome()
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username='randomtester', email='user@example.com')
        self.access_token = "secret"
        self.usa = UserSocialAuth.objects.create(
            user=self.user, provider='drchrono',
            uid='1234',
            extra_data={
                "access_token": self.access_token,
                "expires_in": 172800,
                "refresh_token": "wWdSgnBSwLZs1XEwxxG0CE8JRFNAjm",
                "auth_time": 1575496917})

    def test_get_token(self):
        token = self.doctor_welcome.get_token()
        self.assertEqual(type(token), str)
        self.assertEqual(token, "secret")

        # make sure oauth_provider.extra_data['access_token'] is what it returns
        oauth_provider = UserSocialAuth.objects.get(provider='drchrono')
        self.assertEqual(token, oauth_provider.extra_data['access_token'])

    def test_get_api_request_authorization_failed(self):
        # returns None if it fails
        self.assertEqual(self.doctor_welcome.make_api_request(), None)

    def test_get_context_data(self):
        with self.assertRaises(requests.exceptions.HTTPError):
            self.doctor_welcome.get_context_data()

    def test_doctor_welcome(self):
        with self.assertRaises(requests.exceptions.HTTPError):
            response = self.client.get(reverse('welcome'))


class VisitTimerViewTests(TestCase):
    def setUp(self):
        self.view = VisitTimerView()

    def test_toggle_timer(self):
        # checked-in user
        visit = Visit.objects.create(appointment_id=123, patient_id=123, status="Arrived")

        # toggle on,
        self.view.toggle_timer(123)
        visit.refresh_from_db()
        self.assertEqual("In Session", visit.status)
        self.assertEqual(visit.start_time.day, timezone.now().day)

        time.sleep(1)

        # toggle off, status should be finished now
        self.view.toggle_timer(123)
        visit.refresh_from_db()
        self.assertEqual("Finished", visit.status)
        self.assertEqual(visit.end_time.day, timezone.now().day)

        # duration should be 1 second
        self.assertEqual(visit.get_visit_duration().seconds, 1)

        # should raise an exception
        with self.assertRaises(Exception):
            self.view.toggle_timer(123)

    def test_post(self):
        # checked-in user
        visit = Visit.objects.create(appointment_id=123, patient_id=123, status="Test")

        with self.assertRaises(Exception):
            self.client.post(reverse('timer'), data={'appointment_id': 123})

        # if status is arrived, after running should be In Session
        visit.status = "Arrived"
        visit.save()
        response = self.client.post(reverse('timer'), data={'appointment_id': 123})
        visit.refresh_from_db()
        self.assertEqual("In Session", visit.status)

        # after running one more time should be Finished
        response = self.client.post(reverse('timer'), data={'appointment_id': 123})
        visit.refresh_from_db()
        self.assertEqual("Finished", visit.status)

        # and if you ran one more time should raise exception
        with self.assertRaises(Exception):
            self.client.post(reverse('timer'), data={'appointment_id': 123})


class CheckInViewTests(TestCase):
    def setUp(self):
        self.view = CheckInView()

    def test_get(self):
        # should always return a 200
        response = self.client.get(reverse('check-in'))
        self.assertEqual(200, response.status_code)

    def test_post(self):
        # should return 200
        response = self.client.post(reverse('check-in'), data={'first_name': 'test', 'last_name': 'test'})
        self.assertEqual(response.status_code, 200)


class DemographicViewTests(TestCase):
    def setUp(self):
        self.view = DemographicView()

    def test_get(self):
        # should return a 404 if not authed
        response = self.client.get(reverse('demographics'))
        self.assertEqual(404, response.status_code)

    def test_post(self):
        # should return 200
        response = self.client.post(reverse('demographics'))
        self.assertEqual(200, response.status_code)
