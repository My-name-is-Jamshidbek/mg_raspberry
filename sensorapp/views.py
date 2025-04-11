from rest_framework import generics
from .models import SensorData
from .serializers import SensorDataSerializer

# This view allows POST to create a new sensor record
# and GET to list existing sensor records.
class SensorDataListCreateView(generics.ListCreateAPIView):
    queryset = SensorData.objects.all().order_by('-timestamp')
    serializer_class = SensorDataSerializer
