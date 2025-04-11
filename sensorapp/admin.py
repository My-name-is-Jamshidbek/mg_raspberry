from django.contrib import admin
from .models import SensorData

@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'controller', 'timestamp')
    list_filter = ('device_id', 'controller', 'timestamp')
