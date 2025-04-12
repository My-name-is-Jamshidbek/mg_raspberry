from rest_framework import generics
from .serializers import SensorDataSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import SensorData
from django.forms.models import model_to_dict

# This view allows POST to create a new sensor record
# and GET to list existing sensor records.
class SensorDataListCreateView(generics.ListCreateAPIView):
    queryset = SensorData.objects.all().order_by('-timestamp')
    serializer_class = SensorDataSerializer


@api_view(['POST'])
def save_sensor_data(request):
    try:
        data = request.data
        sensor_record = SensorData(
            device_id=data.get("device_id", ""),
            controller=data.get("controller", ""),
            temperature=data.get("temperature"),
            humidity=data.get("humidity"),
            cmk=data.get("cmk", []),
            motion=data.get("motion", []),
            button=not data.get("button", False),
            gas=data.get("gas"),
        )
        sensor_record.save()
        return Response({"message": "Sensor data saved."}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def latest_sensor(request):
    latest = SensorData.objects.order_by('-timestamp').first()
    if latest:
        return Response(model_to_dict(latest))
    return Response({}, status=204)

@api_view(['GET'])
def prev_sensor(request):
    prev = SensorData.objects.order_by('-timestamp')[1:2].first()
    if prev:
        return Response(model_to_dict(prev))
    return Response({}, status=204)
