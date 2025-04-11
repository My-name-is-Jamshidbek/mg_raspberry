from django.db import models

class SensorData(models.Model):
    device_id   = models.CharField(max_length=20)
    controller  = models.CharField(max_length=50)
    # Use FloatField with null=True so that NaN readings can be represented as null in the database.
    temperature = models.FloatField(null=True, blank=True)
    humidity    = models.FloatField(null=True, blank=True)
    # Use JSONField to store array data (requires Django 3.1+)
    cmk         = models.JSONField(null=True, blank=True)
    motion      = models.JSONField(null=True, blank=True)
    button      = models.BooleanField(default=False)
    gas         = models.FloatField(null=True, blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Data from device {self.device_id} at {self.timestamp}"
