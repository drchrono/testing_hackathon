from django.test import TestCase
from requests import HTTPError

from social_auth_drchrono.backends import drchronoOAuth2


class TestDrchronoOAuth2(TestCase):
    def setUp(self):
        self.oauth_client = drchronoOAuth2(strategy=None)

    def test_get_user_details(self):
        self.assertEqual(self.oauth_client.get_user_details({'username': 'test'}), {'username': 'test'})

    def test_get_auth_header(self):
        self.assertEqual(self.oauth_client.get_auth_header("secret").get('Authorization'), 'Bearer secret')

    def test_user_data(self):
        self.client.USER_DATA_URL = ""
        with self.assertRaises(HTTPError):
            self.assertEqual(self.oauth_client.user_data({'username': 'test'}), 'test')
