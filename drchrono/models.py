from datetime import timezone

from django.db import models
from django.utils import timezone


class Visit(models.Model):
    """
    Used to keep track of length of visit
    """
    appointment_id = models.IntegerField(unique=True)
    patient_id = models.IntegerField()
    status = models.CharField(max_length=50, blank=True, null=True)
    scheduled_time = models.DateTimeField(blank=True, null=True)
    arrival_time = models.DateTimeField(null=True)
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)

    def get_wait_duration(self):
        if not self.arrival_time:
            return "Hasn't arrived"
        if self.start_time:
            return self.start_time - self.arrival_time
        return timezone.now() - self.arrival_time 

    def get_visit_duration(self):
        if not self.start_time:
            return "Visit hasn't started"
        if self.end_time:
            return self.start_time - self.end_time
        return timezone.now() - self.start_time

    def __repr__(self):
        return f"<Visit {self.appointment_id}>"
