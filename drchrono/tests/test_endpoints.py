from types import GeneratorType

from django.test import TestCase

from drchrono.endpoints import BaseEndpoint, ERROR_CODES, APIException, AppointmentEndpoint


class TestBaseEndpoint(TestCase):
    def setUp(cls):
        cls.access_token = "secret"
        cls.client = BaseEndpoint(cls.access_token)

    def test_base_url(self):
        self.assertEqual(self.client.BASE_URL, 'https://drchrono.com/api/')

    def test_init(self):
        # set access_token
        self.assertEqual(self.client.access_token, self.access_token)

    def test_url(self):
        self.assertEqual(self.client._url("test"), "{}{}/{}".format(self.client.BASE_URL, self.client.endpoint, "test"))
        self.assertEqual(self.client._url(), "{}{}".format(self.client.BASE_URL, self.client.endpoint))

    def test_auth_headers(self):
        kwargs = {}
        self.assertEqual(self.client._auth_headers(kwargs), None)
        self.assertEqual(kwargs,
                         {
                             'headers': {
                                 'Authorization': 'Bearer {}'.format(self.access_token)
                             }
                         })

    def test_json_or_exception(self):
        # after switching to python 3 make generic using data classes
        class Response:
            ok = False
            status_code = 666
            content = "test"

        response = Response()
        with self.assertRaises(ERROR_CODES.get(response.status_code, APIException)):
            self.client._json_or_exception(response)

        class Response:
            ok = True
            status_code = 204
            content = "test"

        response = Response()
        self.assertEqual(self.client._json_or_exception(response), None)

        class Response:
            ok = True
            status_code = 200
            content = "test"

            def json(self):
                return "test"

        response = Response()
        self.assertEqual(self.client._json_or_exception(response), response.json())

    def test_list(self):
        # Returns an iterator
        self.assertEqual(type(self.client.list()), GeneratorType)

        # request should fail, and raises a value error when trying to do response.json()
        with self.assertRaises(ValueError):
            next(self.client.list())

    def test_fetch(self):
        self.client.endpoint = 'doctors'
        with self.assertRaises(APIException):
            self.client.fetch(None, {})

    def test_create(self):
        self.client.endpoint = 'doctors'
        with self.assertRaises(APIException):
            self.client.create()

    def test_update(self):
        self.client.endpoint = 'doctors'
        with self.assertRaises(APIException):
            self.client.update(1, {})

    def test_delete(self):
        self.client.endpoint = 'doctors'
        kw = {}
        with self.assertRaises(APIException):
            self.client.delete(1)


class TestAppointmentEndpoint(TestCase):
    def setUp(self):
        self.client = AppointmentEndpoint()

    def test_list(self):
        # will raise an exception if you don't provide with params that has date or datetime key
        with self.assertRaises(Exception):
            self.client.list()

        # Returns an iterator
        self.assertEqual(type(self.client.list(params={'date': None})), GeneratorType)

        # request should fail, and raises a value error when trying to do response.json()
        with self.assertRaises(APIException):
            next(self.client.list(params={'date': None}))
