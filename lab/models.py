from django.db import models
from django.conf import settings

# LabTest Model
class LabTest(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    instructions = models.TextField(help_text="e.g. fasting required", blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.name

# LabSchedule Model
class LabSchedule(models.Model):
    DAY_CHOICES = (
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    )

    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    is_open = models.BooleanField(default=True)

    def __str__(self):
        return self.day_of_week

# LabBooking Model

class LabBooking(models.Model):
    STATUS_CHOICES = (
        ('booked', 'Booked'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='lab_bookings')
    test = models.ForeignKey(LabTest,on_delete=models.CASCADE)
    booking_date = models.DateTimeField(auto_now_add=True)
    test_date = models.DateField()
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='booked' )

    def __str__(self):
        return f"{self.user.username} - {self.test.name}"
    
# LabReport Model
class LabReport(models.Model):

    booking = models.OneToOneField(LabBooking,on_delete=models.CASCADE,related_name='report')
    report_file = models.FileField(upload_to='lab_reports/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,limit_choices_to={'role': 'lab_technician'})
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for {self.booking.test.name}"