from django.urls import path
from .views import SensorDataListCreateView, save_sensor_data, latest_sensor, prev_sensor

urlpatterns = [
    path('data/', SensorDataListCreateView.as_view(), name='sensor-data'),
    path('api/save-sensor-data/', save_sensor_data, name='save-sensor-data'),
    path('api/latest-sensor/', latest_sensor),
    path('api/prev-sensor/', prev_sensor),
]
