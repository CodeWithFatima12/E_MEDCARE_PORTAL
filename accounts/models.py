from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),  # default
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
        ('pharmacist', 'Pharmacist'),
        ('lab_technician', 'Lab Technician'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')