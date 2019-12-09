from types import GeneratorType

from django.test import TestCase

from drchrono.endpoints import BaseEndpoint, ERROR_CODES, APIException, AppointmentEndpoint


class TestBaseEndpoint(TestCase):
    def setUp(self):
        self.access_token = "secret"
        self.endpoint = BaseEndpoint(self.access_token)

    def test_base_url(self):
        self.assertEqual(self.endpoint.BASE_URL, 'https://drchrono.com/api/')

    def test_init(self):
        # set access_token
        self.assertEqual(self.endpoint.access_token, self.access_token)

    def test_url(self):
        self.assertEqual(self.endpoint._url("test"),
                         "{}{}/{}".format(self.endpoint.BASE_URL, self.endpoint.endpoint, "test"))
        self.assertEqual(self.endpoint._url(), "{}{}".format(self.endpoint.BASE_URL, self.endpoint.endpoint))

    def test_auth_headers(self):
        kwargs = {}
        self.assertEqual(self.endpoint._auth_headers(kwargs), None)
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
            self.endpoint._json_or_exception(response)

        class Response:
            ok = True
            status_code = 204
            content = "test"

        response = Response()
        self.assertEqual(self.endpoint._json_or_exception(response), None)

        class Response:
            ok = True
            status_code = 200
            content = "test"

            def json(self):
                return "test"

        response = Response()
        self.assertEqual(self.endpoint._json_or_exception(response), response.json())

    def test_list(self):
        # Returns an iterator
        self.assertEqual(type(self.endpoint.list()), GeneratorType)

        # request should fail, and raises a value error when trying to do response.json()
        with self.assertRaises(ValueError):
            next(self.endpoint.list())

    def test_fetch(self):
        self.endpoint.endpoint = 'doctors'
        with self.assertRaises(APIException):
            self.endpoint.fetch(None, {})

    def test_create(self):
        self.endpoint.endpoint = 'doctors'
        with self.assertRaises(APIException):
            self.endpoint.create()

    def test_update(self):
        self.endpoint.endpoint = 'doctors'
        with self.assertRaises(APIException):
            self.endpoint.update(1, {})

    def test_delete(self):
        self.endpoint.endpoint = 'doctors'
        kw = {}
        with self.assertRaises(APIException):
            self.endpoint.delete(1)


class TestAppointmentEndpoint(TestCase):
    def setUp(self):
        self.endpoint = AppointmentEndpoint()

    def test_list(self):
        # will raise an exception if you don't provide with params that has date or datetime key
        with self.assertRaises(Exception):
            self.endpoint.list()

        # Returns an iterator
        self.assertEqual(type(self.endpoint.list(params={'date': None})), GeneratorType)

        # request should fail, and raises a value error when trying to do response.json()
        with self.assertRaises(APIException):
            next(self.endpoint.list(params={'date': None}))
