from django.contrib import admin
from .models import LabTest,LabSchedule,LabBooking
# Register your models here.


admin.site.register(LabTest)
admin.site.register(LabSchedule)
admin.site.register(LabBooking)