from rest_framework import serializers
from .models import LabTest, LabSchedule

class LabTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTest
        fields = ['id', 'name', 'description', 'instructions', 'price']

class LabScheduleSerializer(serializers.ModelSerializer):
    # get_day_of_week_display() ko use karne ke liye hum SerializerMethodField use kar sakte hain
    # taake 'monday' ki jagah 'Monday' nazar aaye
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = LabSchedule
        fields = ['id', 'day_of_week', 'day_display', 'is_open']