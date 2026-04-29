from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings

class HealthMetric(models.Model):
    # Link to your Custom User
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    glucose_level = models.IntegerField()
    bmi = models.FloatField()
    hba1c = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} - {self.created_at.date()}"