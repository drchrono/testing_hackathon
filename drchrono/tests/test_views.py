import requests
from django.contrib.auth import get_user_model
from django.test import TestCase
from social_django.models import UserSocialAuth

from drchrono.endpoints import DoctorEndpoint
from drchrono.views import DoctorWelcome


class SetupViewTests(TestCase):
    def test_kiosk_setup(self):
        response = self.client.get('/setup/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'<a href="/login/drchrono/">\n      Set up your Check-in kiosk by logging into drchrono!\n    </a>\n',
            response.content)


class DoctorWelcomeTests(TestCase):
    def setUp(cls):
        cls.doctor_endpoint = DoctorEndpoint()
        cls.doctor_welcome = DoctorWelcome()
        cls.user_model = get_user_model()
        cls.user = cls.user_model.objects.create_user(
            username='randomtester', email='user@example.com')
        cls.access_token = "secret"
        cls.usa = UserSocialAuth.objects.create(
            user=cls.user, provider='drchrono',
            uid='1234',
            extra_data={
                "access_token": cls.access_token,
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
            response = self.client.get('/welcome/')
