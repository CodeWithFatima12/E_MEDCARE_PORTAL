from rest_framework import serializers
from .models import HealthMetric

class HealthMetricSerializer(serializers.ModelSerializer):
    # We format the date here so the Chart can read it easily
    date = serializers.DateTimeField(source='created_at', format='%d %b %Y')

    class Meta:
        model = HealthMetric
        fields = ['glucose_level', 'bmi', 'hba1c', 'date']