from django.contrib import admin
from .models import Department, Doctor, DoctorSchedule, TimeSlot, Appointment, Prescription

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'experience', 'consultation_fee')
    list_filter = ('department',)

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'appointment_type', 'status', 'created_at')
    list_filter = ('status', 'appointment_type')
    search_fields = ('patient__username', 'doctor__user__username')

admin.site.register(DoctorSchedule)
admin.site.register(TimeSlot)
admin.site.register(Prescription)
# Register your models here.
