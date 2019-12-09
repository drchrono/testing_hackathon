from datetime import datetime, timezone, timedelta

from django.test import TestCase

from drchrono.models import Visit


class TestVisit(TestCase):
    def setUp(self):
        self.visit = Visit()

    def test_get_wait_duration(self):
        # if there is no arrival time, should return Hasn't arrived
        self.assertEqual("Hasn't arrived", self.visit.get_wait_duration())

        # after setting arrival time, and waiting one second, check Visit.get_wait_duration
        self.visit.arrival_time = datetime.now(timezone.utc)
        duration = self.visit.get_wait_duration()
        self.assertEqual(timedelta, type(duration))
        self.assertEqual(0, duration.seconds)

        # after setting a start_time one second in the future, wait duration should be 1 second
        self.visit.start_time = datetime.now(timezone.utc) + timedelta(seconds=1)
        duration = self.visit.get_wait_duration()
        self.assertEqual(timedelta, type(duration))
        self.assertEqual(1, duration.seconds)

    def test_get_visit_duration(self):
        # if start_time is not set, should return Visit hasn't started
        self.assertEqual("Visit hasn't started", self.visit.get_visit_duration())

        # if start_time IS set, should return a timedelta with seconds of 0
        self.visit.start_time = datetime.now(timezone.utc)
        duration = self.visit.get_visit_duration()
        self.assertEqual(timedelta, type(duration))
        self.assertEqual(0, duration.seconds)

        # if set set end_time to 1 second in the future, should return a timedelta with seconds of 1
        self.visit.end_time = datetime.now(timezone.utc) + timedelta(seconds=1)
        duration = self.visit.get_visit_duration()
        self.assertEqual(timedelta, type(duration))
        self.assertEqual(1, duration.seconds)
