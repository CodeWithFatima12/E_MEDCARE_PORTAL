from django.db import models
from django.conf import settings


# Department Table
class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)


# Doctor table
class Doctor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    experience = models.IntegerField()
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    profile_image = models.ImageField(upload_to='doctors/', null=True, blank=True)

    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name}"


#DoctorSchedule Table    
class DoctorSchedule(models.Model):
    DAYS_OF_WEEK = (
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    )

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    class Meta:
        # This prevents a doctor from having two schedules for the same day
        unique_together = ('doctor', 'day_of_week')

    def __str__(self):
        return f"{self.doctor} - {self.get_day_of_week_display()}"

# TimeSlot Table
class TimeSlot(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False)


# Appointment Table
# class Appointment(models.Model):

#     STATUS_CHOICES = (
#         ('pending', 'Pending'),
#         ('confirmed', 'Confirmed'),
#         ('completed', 'Completed'),
#         ('cancelled', 'Cancelled'),
#     )

#     TYPE_CHOICES = (
#         ('online', 'Online'),
#         ('in_hospital', 'In Hospital'),
#     )

#     patient = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='patient_appointments')
#     doctor = models.ForeignKey('Doctor',on_delete=models.CASCADE,related_name='doctor_appointments')
#     slot = models.ForeignKey('TimeSlot', on_delete=models.CASCADE)
#     appointment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
#     medical_history = models.TextField(blank=True)
#     status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending')
#     meeting_link = models.URLField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.patient.username} - {self.doctor.user.username}"

class Appointment(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    TYPE_CHOICES = (
        ('online', 'Online'),
        ('in_hospital', 'In Hospital'),
    )

    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    )

    # Existing fields
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_appointments')
    doctor = models.ForeignKey('Doctor', on_delete=models.CASCADE, related_name='doctor_appointments')
    slot = models.ForeignKey('TimeSlot', on_delete=models.CASCADE)
    appointment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    medical_history = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    meeting_link = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    #  NEW FIELDS WITH null=True, blank=True
    patient_name = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)

    def __str__(self):
        return f"{self.patient.username} - {self.doctor.user.username}"


# Prescription Table
class Prescription(models.Model):

    appointment = models.OneToOneField('Appointment',on_delete=models.CASCADE)
    doctor = models.ForeignKey('Doctor',on_delete=models.CASCADE)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='prescriptions')
    notes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prescription for {self.patient.username}"
