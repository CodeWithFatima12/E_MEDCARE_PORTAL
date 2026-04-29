from rest_framework import serializers
from .models import Doctor, Department, DoctorSchedule, Appointment, Prescription


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description']


class DoctorScheduleSerializer(serializers.ModelSerializer):
    # Time ko 09:00 AM format mein dikhane ke liye
    start_time = serializers.TimeField(format="%I:%M %p")
    end_time = serializers.TimeField(format="%I:%M %p")
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = DoctorSchedule
        fields = ['day_of_week', 'day_display', 'start_time', 'end_time', 'is_available']


class DoctorSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    schedules = DoctorScheduleSerializer(many=True, read_only=True)
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = ['id', 'name', 'department_name', 'experience', 'consultation_fee', 'profile_image', 'schedules']

    def get_name(self, obj):
        return f"Dr. {obj.user.first_name} {obj.user.last_name}"

    def get_profile_image(self, obj):
        if obj.profile_image:
            img_path = str(obj.profile_image)
            if img_path.startswith('media/') or img_path.startswith('/media/'):
                return f"/{img_path.lstrip('/')}"
            return f"/media/{img_path}"
        return "/static/images/doctors/default.png"


# ==================== PATIENT DASHBOARD SERIALIZERS ====================

class PatientAppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    doctor_department = serializers.SerializerMethodField()
    doctor_profile_image = serializers.SerializerMethodField()
    appointment_date = serializers.SerializerMethodField()
    appointment_time = serializers.SerializerMethodField()
    appointment_end_time = serializers.SerializerMethodField()
    has_prescription = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'doctor_name', 'doctor_department', 'doctor_profile_image',
            'appointment_date', 'appointment_time', 'appointment_end_time',
            'appointment_type', 'medical_history', 'status', 'meeting_link',
            'has_prescription', 'created_at',
            # NEW FIELDS ADDED
            'patient_name', 'phone_number', 'age', 'gender'
        ]
    
    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.user.first_name} {obj.doctor.user.last_name}"
    
    def get_doctor_department(self, obj):
        return obj.doctor.department.name if obj.doctor.department else "General"
    
    def get_doctor_profile_image(self, obj):
        if obj.doctor.profile_image:
            img_path = str(obj.doctor.profile_image)
            if img_path.startswith('media/') or img_path.startswith('/media/'):
                return f"/{img_path.lstrip('/')}"
            return f"/media/{img_path}"
        return "/static/images/doctors/default.png"
    
    def get_appointment_date(self, obj):
        return obj.slot.date.strftime("%d %b, %Y")
    
    def get_appointment_time(self, obj):
        return obj.slot.start_time.strftime("%I:%M %p")
    
    def get_appointment_end_time(self, obj):
        return obj.slot.end_time.strftime("%I:%M %p")
    
    def get_has_prescription(self, obj):
        try:
            return hasattr(obj, 'prescription')
        except:
            return False


class PrescriptionDetailSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    doctor_qualification = serializers.SerializerMethodField()
    appointment_date = serializers.SerializerMethodField()
    
    # NEW FIELDS - Patient info from appointment
    patient_name = serializers.SerializerMethodField()
    patient_age = serializers.SerializerMethodField()
    patient_gender = serializers.SerializerMethodField()
    patient_phone = serializers.SerializerMethodField()
    
    class Meta:
        model = Prescription
        fields = ['id', 'doctor_name', 'doctor_qualification', 'notes', 
                  'appointment_date', 'created_at',
                  # NEW FIELDS ADDED
                  'patient_name', 'patient_age', 'patient_gender', 'patient_phone']
    
    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.user.first_name} {obj.doctor.user.last_name}"
    
    def get_doctor_qualification(self, obj):
        return f"{obj.doctor.experience}+ Years Experience | {obj.doctor.department.name}"
    
    def get_appointment_date(self, obj):
        return obj.appointment.slot.date.strftime("%d %b, %Y")
    
    # NEW METHODS
    def get_patient_name(self, obj):
        if obj.appointment.patient_name:
            return obj.appointment.patient_name.title()
        return f"{obj.patient.first_name} {obj.patient.last_name}".title()
    
    def get_patient_age(self, obj):
        return obj.appointment.age if obj.appointment.age else 'Not provided'
    
    def get_patient_gender(self, obj):
        return obj.appointment.gender if obj.appointment.gender else 'Not provided'
    
    def get_patient_phone(self, obj):
        return obj.appointment.phone_number if obj.appointment.phone_number else 'Not provided'


# ==================== DOCTOR DASHBOARD SERIALIZERS ====================

class DoctorAppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    patient_email = serializers.SerializerMethodField()
    patient_phone = serializers.SerializerMethodField()
    # ✅ NEW FIELDS ADDED - age and gender
    age = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    appointment_date = serializers.SerializerMethodField()
    appointment_time = serializers.SerializerMethodField()
    appointment_end_time = serializers.SerializerMethodField()
    has_prescription = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient_name', 'patient_email', 'patient_phone',
            'age', 'gender',  # ✅ ADDED HERE
            'appointment_date', 'appointment_time', 'appointment_end_time',
            'appointment_type', 'medical_history', 'status', 'meeting_link',
            'has_prescription', 'created_at', 'can_cancel'
        ]
    
    def get_patient_name(self, obj):
        if obj.patient_name:
            return obj.patient_name.title()
        return f"{obj.patient.first_name} {obj.patient.last_name}".title()
    
    def get_patient_email(self, obj):
        return obj.patient.email
    
    def get_patient_phone(self, obj):
        if obj.phone_number:
            return obj.phone_number
        return getattr(obj.patient, 'phone', 'Not provided')
    
    # ✅ NEW METHODS - age and gender
    def get_age(self, obj):
        if obj.age:
            return obj.age
        return None
    
    def get_gender(self, obj):
        if obj.gender:
            return obj.gender
        return None
    
    def get_appointment_date(self, obj):
        return obj.slot.date.strftime("%d %b, %Y")
    
    def get_appointment_time(self, obj):
        return obj.slot.start_time.strftime("%I:%M %p")
    
    def get_appointment_end_time(self, obj):
        return obj.slot.end_time.strftime("%I:%M %p")
    
    def get_has_prescription(self, obj):
        try:
            return hasattr(obj, 'prescription')
        except:
            return False
    
    def get_can_cancel(self, obj):
        """Doctor can cancel any confirmed appointment (today or future)"""
        from datetime import date
        return obj.status == 'confirmed' and obj.slot.date >= date.today()


class DoctorScheduleUpdateSerializer(serializers.ModelSerializer):
    start_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M", "%I:%M %p"])
    end_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M", "%I:%M %p"])
    
    class Meta:
        model = DoctorSchedule
        fields = ['day_of_week', 'start_time', 'end_time', 'is_available']

#missing gender age 
# from rest_framework import serializers
# from .models import Doctor, Department, DoctorSchedule, Appointment, Prescription


# class DepartmentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Department
#         fields = ['id', 'name', 'description']


# class DoctorScheduleSerializer(serializers.ModelSerializer):
#     # Time ko 09:00 AM format mein dikhane ke liye
#     start_time = serializers.TimeField(format="%I:%M %p")
#     end_time = serializers.TimeField(format="%I:%M %p")
#     day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

#     class Meta:
#         model = DoctorSchedule
#         fields = ['day_of_week', 'day_display', 'start_time', 'end_time', 'is_available']


# class DoctorSerializer(serializers.ModelSerializer):
#     name = serializers.SerializerMethodField()
#     department_name = serializers.CharField(source='department.name', read_only=True)
#     schedules = DoctorScheduleSerializer(many=True, read_only=True)
#     profile_image = serializers.SerializerMethodField()

#     class Meta:
#         model = Doctor
#         fields = ['id', 'name', 'department_name', 'experience', 'consultation_fee', 'profile_image', 'schedules']

#     def get_name(self, obj):
#         return f"Dr. {obj.user.first_name} {obj.user.last_name}"

#     def get_profile_image(self, obj):
#         if obj.profile_image:
#             img_path = str(obj.profile_image)
#             if img_path.startswith('media/') or img_path.startswith('/media/'):
#                 return f"/{img_path.lstrip('/')}"
#             return f"/media/{img_path}"
#         return "/static/images/doctors/default.png"


# # ==================== PATIENT DASHBOARD SERIALIZERS ====================

# class PatientAppointmentSerializer(serializers.ModelSerializer):
#     doctor_name = serializers.SerializerMethodField()
#     doctor_department = serializers.SerializerMethodField()
#     doctor_profile_image = serializers.SerializerMethodField()
#     appointment_date = serializers.SerializerMethodField()
#     appointment_time = serializers.SerializerMethodField()
#     appointment_end_time = serializers.SerializerMethodField()
#     has_prescription = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Appointment
#         fields = [
#             'id', 'doctor_name', 'doctor_department', 'doctor_profile_image',
#             'appointment_date', 'appointment_time', 'appointment_end_time',
#             'appointment_type', 'medical_history', 'status', 'meeting_link',
#             'has_prescription', 'created_at',
#             # 🔴 NEW FIELDS ADDED
#             'patient_name', 'phone_number', 'age', 'gender'
#         ]
    
#     def get_doctor_name(self, obj):
#         return f"Dr. {obj.doctor.user.first_name} {obj.doctor.user.last_name}"
    
#     def get_doctor_department(self, obj):
#         return obj.doctor.department.name if obj.doctor.department else "General"
    
#     def get_doctor_profile_image(self, obj):
#         if obj.doctor.profile_image:
#             img_path = str(obj.doctor.profile_image)
#             if img_path.startswith('media/') or img_path.startswith('/media/'):
#                 return f"/{img_path.lstrip('/')}"
#             return f"/media/{img_path}"
#         return "/static/images/doctors/default.png"
    
#     def get_appointment_date(self, obj):
#         return obj.slot.date.strftime("%d %b, %Y")
    
#     def get_appointment_time(self, obj):
#         return obj.slot.start_time.strftime("%I:%M %p")
    
#     def get_appointment_end_time(self, obj):
#         return obj.slot.end_time.strftime("%I:%M %p")
    
#     def get_has_prescription(self, obj):
#         try:
#             return hasattr(obj, 'prescription')
#         except:
#             return False


# class PrescriptionDetailSerializer(serializers.ModelSerializer):
#     doctor_name = serializers.SerializerMethodField()
#     doctor_qualification = serializers.SerializerMethodField()
#     appointment_date = serializers.SerializerMethodField()
    
#     # 🔴 NEW FIELDS - Patient info from appointment
#     patient_name = serializers.SerializerMethodField()
#     patient_age = serializers.SerializerMethodField()
#     patient_gender = serializers.SerializerMethodField()
#     patient_phone = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Prescription
#         fields = ['id', 'doctor_name', 'doctor_qualification', 'notes', 
#                   'appointment_date', 'created_at',
#                   # 🔴 NEW FIELDS ADDED
#                   'patient_name', 'patient_age', 'patient_gender', 'patient_phone']
    
#     def get_doctor_name(self, obj):
#         return f"Dr. {obj.doctor.user.first_name} {obj.doctor.user.last_name}"
    
#     def get_doctor_qualification(self, obj):
#         return f"{obj.doctor.experience}+ Years Experience | {obj.doctor.department.name}"
    
#     def get_appointment_date(self, obj):
#         return obj.appointment.slot.date.strftime("%d %b, %Y")
    
#     # 🔴 NEW METHODS
#     def get_patient_name(self, obj):
#         if obj.appointment.patient_name:
#             return obj.appointment.patient_name
#         return f"{obj.patient.first_name} {obj.patient.last_name}"
    
#     def get_patient_age(self, obj):
#         return obj.appointment.age if obj.appointment.age else 'Not provided'
    
#     def get_patient_gender(self, obj):
#         return obj.appointment.gender if obj.appointment.gender else 'Not provided'
    
#     def get_patient_phone(self, obj):
#         return obj.appointment.phone_number if obj.appointment.phone_number else 'Not provided'


# # ==================== DOCTOR DASHBOARD SERIALIZERS ====================

# class DoctorAppointmentSerializer(serializers.ModelSerializer):
#     patient_name = serializers.SerializerMethodField()
#     patient_email = serializers.SerializerMethodField()
#     patient_phone = serializers.SerializerMethodField()
#     appointment_date = serializers.SerializerMethodField()
#     appointment_time = serializers.SerializerMethodField()
#     appointment_end_time = serializers.SerializerMethodField()
#     has_prescription = serializers.SerializerMethodField()
#     can_cancel = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Appointment
#         fields = [
#             'id', 'patient_name', 'patient_email', 'patient_phone',
#             'appointment_date', 'appointment_time', 'appointment_end_time',
#             'appointment_type', 'medical_history', 'status', 'meeting_link',
#             'has_prescription', 'created_at', 'can_cancel'
#         ]
    
#     def get_patient_name(self, obj):
#         if obj.patient_name:
#             return obj.patient_name
#         return f"{obj.patient.first_name} {obj.patient.last_name}"
    
#     def get_patient_email(self, obj):
#         return obj.patient.email
    
#     def get_patient_phone(self, obj):
#         if obj.phone_number:
#             return obj.phone_number
#         return getattr(obj.patient, 'phone', 'Not provided')
    
#     def get_appointment_date(self, obj):
#         return obj.slot.date.strftime("%d %b, %Y")
    
#     def get_appointment_time(self, obj):
#         return obj.slot.start_time.strftime("%I:%M %p")
    
#     def get_appointment_end_time(self, obj):
#         return obj.slot.end_time.strftime("%I:%M %p")
    
#     def get_has_prescription(self, obj):
#         try:
#             return hasattr(obj, 'prescription')
#         except:
#             return False
    
#     def get_can_cancel(self, obj):
#         """Doctor can cancel any confirmed appointment (today or future)"""
#         from datetime import date
#         return obj.status == 'confirmed' and obj.slot.date >= date.today()


# class DoctorScheduleUpdateSerializer(serializers.ModelSerializer):
#     start_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M", "%I:%M %p"])
#     end_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M", "%I:%M %p"])
    
#     class Meta:
#         model = DoctorSchedule
#         fields = ['day_of_week', 'start_time', 'end_time', 'is_available']



#missing appointment name,age gender fields
# from rest_framework import serializers
# from .models import Doctor, Department, DoctorSchedule, Appointment, Prescription


# class DepartmentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Department
#         fields = ['id', 'name', 'description']


# class DoctorScheduleSerializer(serializers.ModelSerializer):
#     # Time ko 09:00 AM format mein dikhane ke liye
#     start_time = serializers.TimeField(format="%I:%M %p")
#     end_time = serializers.TimeField(format="%I:%M %p")
#     day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

#     class Meta:
#         model = DoctorSchedule
#         fields = ['day_of_week', 'day_display', 'start_time', 'end_time', 'is_available']


# class DoctorSerializer(serializers.ModelSerializer):
#     name = serializers.SerializerMethodField()
#     department_name = serializers.CharField(source='department.name', read_only=True)
#     schedules = DoctorScheduleSerializer(many=True, read_only=True)
#     profile_image = serializers.SerializerMethodField()

#     class Meta:
#         model = Doctor
#         fields = ['id', 'name', 'department_name', 'experience', 'consultation_fee', 'profile_image', 'schedules']

#     def get_name(self, obj):
#         return f"Dr. {obj.user.first_name} {obj.user.last_name}"

#     def get_profile_image(self, obj):
#         if obj.profile_image:
#             img_path = str(obj.profile_image)
#             if img_path.startswith('media/') or img_path.startswith('/media/'):
#                 return f"/{img_path.lstrip('/')}"
#             return f"/media/{img_path}"
#         return "/static/images/doctors/default.png"


# # ==================== PATIENT DASHBOARD SERIALIZERS ====================

# class PatientAppointmentSerializer(serializers.ModelSerializer):
#     doctor_name = serializers.SerializerMethodField()
#     doctor_department = serializers.SerializerMethodField()
#     doctor_profile_image = serializers.SerializerMethodField()
#     appointment_date = serializers.SerializerMethodField()
#     appointment_time = serializers.SerializerMethodField()
#     appointment_end_time = serializers.SerializerMethodField()
#     has_prescription = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Appointment
#         fields = [
#             'id', 'doctor_name', 'doctor_department', 'doctor_profile_image',
#             'appointment_date', 'appointment_time', 'appointment_end_time',
#             'appointment_type', 'medical_history', 'status', 'meeting_link',
#             'has_prescription', 'created_at'
#         ]
    
#     def get_doctor_name(self, obj):
#         return f"Dr. {obj.doctor.user.first_name} {obj.doctor.user.last_name}"
    
#     def get_doctor_department(self, obj):
#         return obj.doctor.department.name if obj.doctor.department else "General"
    
#     def get_doctor_profile_image(self, obj):
#         if obj.doctor.profile_image:
#             img_path = str(obj.doctor.profile_image)
#             if img_path.startswith('media/') or img_path.startswith('/media/'):
#                 return f"/{img_path.lstrip('/')}"
#             return f"/media/{img_path}"
#         return "/static/images/doctors/default.png"
    
#     def get_appointment_date(self, obj):
#         return obj.slot.date.strftime("%d %b, %Y")
    
#     def get_appointment_time(self, obj):
#         return obj.slot.start_time.strftime("%I:%M %p")
    
#     def get_appointment_end_time(self, obj):
#         return obj.slot.end_time.strftime("%I:%M %p")
    
#     def get_has_prescription(self, obj):
#         try:
#             return hasattr(obj, 'prescription')
#         except:
#             return False


# class PrescriptionDetailSerializer(serializers.ModelSerializer):
#     doctor_name = serializers.SerializerMethodField()
#     doctor_qualification = serializers.SerializerMethodField()
#     appointment_date = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Prescription
#         fields = ['id', 'doctor_name', 'doctor_qualification', 'notes', 
#                   'appointment_date', 'created_at']
    
#     def get_doctor_name(self, obj):
#         return f"Dr. {obj.doctor.user.first_name} {obj.doctor.user.last_name}"
    
#     def get_doctor_qualification(self, obj):
#         return f"{obj.doctor.experience}+ Years Experience | {obj.doctor.department.name}"
    
#     def get_appointment_date(self, obj):
#         return obj.appointment.slot.date.strftime("%d %b, %Y")


# # ==================== DOCTOR DASHBOARD SERIALIZERS ====================

# class DoctorAppointmentSerializer(serializers.ModelSerializer):
#     patient_name = serializers.SerializerMethodField()
#     patient_email = serializers.SerializerMethodField()
#     patient_phone = serializers.SerializerMethodField()
#     appointment_date = serializers.SerializerMethodField()
#     appointment_time = serializers.SerializerMethodField()
#     appointment_end_time = serializers.SerializerMethodField()
#     has_prescription = serializers.SerializerMethodField()
#     can_cancel = serializers.SerializerMethodField()  # ADDED FOR CANCEL BUTTON
    
#     class Meta:
#         model = Appointment
#         fields = [
#             'id', 'patient_name', 'patient_email', 'patient_phone',
#             'appointment_date', 'appointment_time', 'appointment_end_time',
#             'appointment_type', 'medical_history', 'status', 'meeting_link',
#             'has_prescription', 'created_at', 'can_cancel'
#         ]
    
#     def get_patient_name(self, obj):
#         return f"{obj.patient.first_name} {obj.patient.last_name}"
    
#     def get_patient_email(self, obj):
#         return obj.patient.email
    
#     def get_patient_phone(self, obj):
#         return getattr(obj.patient, 'phone', 'Not provided')
    
#     def get_appointment_date(self, obj):
#         return obj.slot.date.strftime("%d %b, %Y")
    
#     def get_appointment_time(self, obj):
#         return obj.slot.start_time.strftime("%I:%M %p")
    
#     def get_appointment_end_time(self, obj):
#         return obj.slot.end_time.strftime("%I:%M %p")
    
#     def get_has_prescription(self, obj):
#         try:
#             return hasattr(obj, 'prescription')
#         except:
#             return False
    
#     def get_can_cancel(self, obj):
#         """Doctor can cancel any confirmed appointment (today or future)"""
#         from datetime import date
#         return obj.status == 'confirmed' and obj.slot.date >= date.today()


# class DoctorScheduleUpdateSerializer(serializers.ModelSerializer):
#     start_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M", "%I:%M %p"])
#     end_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M", "%I:%M %p"])
    
#     class Meta:
#         model = DoctorSchedule
#         fields = ['day_of_week', 'start_time', 'end_time', 'is_available']



#doubt
##################################################################





#missing cancel button on doctor dashboard 
# from rest_framework import serializers
# from .models import Doctor, Department, DoctorSchedule, Appointment, Prescription

# class DepartmentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Department
#         fields = ['id', 'name', 'description']

# class DoctorScheduleSerializer(serializers.ModelSerializer):
#     # Time ko 09:00 AM format mein dikhane ke liye
#     start_time = serializers.TimeField(format="%I:%M %p")
#     end_time = serializers.TimeField(format="%I:%M %p")
#     day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

#     class Meta:
#         model = DoctorSchedule
#         fields = ['day_of_week', 'day_display', 'start_time', 'end_time', 'is_available']

# class DoctorSerializer(serializers.ModelSerializer):
#     name = serializers.SerializerMethodField()
#     department_name = serializers.CharField(source='department.name', read_only=True)
#     schedules = DoctorScheduleSerializer(many=True, read_only=True)
#     profile_image = serializers.SerializerMethodField()

#     class Meta:
#         model = Doctor
#         fields = ['id', 'name', 'department_name', 'experience', 'consultation_fee', 'profile_image', 'schedules']

#     def get_name(self, obj):
#         return f"Dr. {obj.user.first_name} {obj.user.last_name}"

#     def get_profile_image(self, obj):
#         if obj.profile_image:
#             img_path = str(obj.profile_image)
#             if img_path.startswith('media/') or img_path.startswith('/media/'):
#                 return f"/{img_path.lstrip('/')}"
#             return f"/media/{img_path}"
#         return "/static/images/doctors/default.png"


# # ==================== PATIENT DASHBOARD SERIALIZERS ====================

# class PatientAppointmentSerializer(serializers.ModelSerializer):
#     doctor_name = serializers.SerializerMethodField()
#     doctor_department = serializers.SerializerMethodField()
#     doctor_profile_image = serializers.SerializerMethodField()
#     appointment_date = serializers.SerializerMethodField()
#     appointment_time = serializers.SerializerMethodField()
#     appointment_end_time = serializers.SerializerMethodField()
#     has_prescription = serializers.SerializerMethodField()
#     can_cancel = serializers.SerializerMethodField()  # ADDED FOR CANCEL BUTTON

    
#     class Meta:
#         model = Appointment
#         fields = [
#             'id', 'doctor_name', 'doctor_department', 'doctor_profile_image',
#             'appointment_date', 'appointment_time', 'appointment_end_time',
#             'appointment_type', 'medical_history', 'status', 'meeting_link',
#             'has_prescription', 'created_at'
#         ]
    
#     def get_doctor_name(self, obj):
#         return f"Dr. {obj.doctor.user.first_name} {obj.doctor.user.last_name}"
    
#     def get_doctor_department(self, obj):
#         return obj.doctor.department.name if obj.doctor.department else "General"
    
#     def get_doctor_profile_image(self, obj):
#         if obj.doctor.profile_image:
#             img_path = str(obj.doctor.profile_image)
#             if img_path.startswith('media/') or img_path.startswith('/media/'):
#                 return f"/{img_path.lstrip('/')}"
#             return f"/media/{img_path}"
#         return "/static/images/doctors/default.png"
    
#     def get_appointment_date(self, obj):
#         return obj.slot.date.strftime("%d %b, %Y")
    
#     def get_appointment_time(self, obj):
#         return obj.slot.start_time.strftime("%I:%M %p")
    
#     def get_appointment_end_time(self, obj):
#         return obj.slot.end_time.strftime("%I:%M %p")
    
#     def get_has_prescription(self, obj):
#         try:
#             return hasattr(obj, 'prescription')
#         except:
#             return False


# class PrescriptionDetailSerializer(serializers.ModelSerializer):
#     doctor_name = serializers.SerializerMethodField()
#     doctor_qualification = serializers.SerializerMethodField()
#     appointment_date = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Prescription
#         fields = ['id', 'doctor_name', 'doctor_qualification', 'notes', 
#                   'appointment_date', 'created_at']
    
#     def get_doctor_name(self, obj):
#         return f"Dr. {obj.doctor.user.first_name} {obj.doctor.user.last_name}"
    
#     def get_doctor_qualification(self, obj):
#         return f"{obj.doctor.experience}+ Years Experience | {obj.doctor.department.name}"
    
#     def get_appointment_date(self, obj):
#         return obj.appointment.slot.date.strftime("%d %b, %Y")


# # ==================== DOCTOR DASHBOARD SERIALIZERS ====================

# class DoctorAppointmentSerializer(serializers.ModelSerializer):
#     patient_name = serializers.SerializerMethodField()
#     patient_email = serializers.SerializerMethodField()
#     patient_phone = serializers.SerializerMethodField()
#     appointment_date = serializers.SerializerMethodField()
#     appointment_time = serializers.SerializerMethodField()
#     appointment_end_time = serializers.SerializerMethodField()
#     has_prescription = serializers.SerializerMethodField()
    
    
#     class Meta:
#         model = Appointment
#         fields = [
#             'id', 'patient_name', 'patient_email', 'patient_phone',
#             'appointment_date', 'appointment_time', 'appointment_end_time',
#             'appointment_type', 'medical_history', 'status', 'meeting_link',
#             'has_prescription', 'created_at'
#         ]
    
#     def get_patient_name(self, obj):
#         return f"{obj.patient.first_name} {obj.patient.last_name}"
    
#     def get_patient_email(self, obj):
#         return obj.patient.email
    
#     def get_patient_phone(self, obj):
#         return getattr(obj.patient, 'phone', 'Not provided')
    
#     def get_appointment_date(self, obj):
#         return obj.slot.date.strftime("%d %b, %Y")
    
#     def get_appointment_time(self, obj):
#         return obj.slot.start_time.strftime("%I:%M %p")
    
#     def get_appointment_end_time(self, obj):
#         return obj.slot.end_time.strftime("%I:%M %p")
    
#     def get_has_prescription(self, obj):
#         try:
#             return hasattr(obj, 'prescription')
#         except:
#             return False
#     def get_can_cancel(self, obj):
#         """Doctor can cancel any confirmed appointment (today or future)"""
#         from datetime import date
#         return obj.status == 'confirmed' and obj.slot.date >= date.today()

# class DoctorScheduleUpdateSerializer(serializers.ModelSerializer):
#     start_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M", "%I:%M %p"])
#     end_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M", "%I:%M %p"])
    
#     class Meta:
#         model = DoctorSchedule
#         fields = ['day_of_week', 'start_time', 'end_time', 'is_available']




#serializer patient dashbaord wlaa 

# from rest_framework import serializers
# from .models import Doctor, Department, DoctorSchedule, Appointment, Prescription

# class DepartmentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Department
#         fields = ['id', 'name', 'description']

# class DoctorScheduleSerializer(serializers.ModelSerializer):
#     # Time ko 09:00 AM format mein dikhane ke liye
#     start_time = serializers.TimeField(format="%I:%M %p")
#     end_time = serializers.TimeField(format="%I:%M %p")
#     day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

#     class Meta:
#         model = DoctorSchedule
#         fields = ['day_of_week', 'day_display', 'start_time', 'end_time', 'is_available']

# class DoctorSerializer(serializers.ModelSerializer):
#     name = serializers.SerializerMethodField()
#     department_name = serializers.CharField(source='department.name', read_only=True)
#     schedules = DoctorScheduleSerializer(many=True, read_only=True)
#     profile_image = serializers.SerializerMethodField()

#     class Meta:
#         model = Doctor
#         fields = ['id', 'name', 'department_name', 'experience', 'consultation_fee', 'profile_image', 'schedules']

#     def get_name(self, obj):
#         return f"Dr. {obj.user.first_name} {obj.user.last_name}"

#     def get_profile_image(self, obj):
#         if obj.profile_image:
#             img_path = str(obj.profile_image)
#             if img_path.startswith('media/') or img_path.startswith('/media/'):
#                 return f"/{img_path.lstrip('/')}"
#             return f"/media/{img_path}"
#         return "/static/images/doctors/default.png"


# # ==================== PATIENT DASHBOARD SERIALIZERS ====================

# class PatientAppointmentSerializer(serializers.ModelSerializer):
#     doctor_name = serializers.SerializerMethodField()
#     doctor_department = serializers.SerializerMethodField()
#     doctor_profile_image = serializers.SerializerMethodField()
#     appointment_date = serializers.SerializerMethodField()
#     appointment_time = serializers.SerializerMethodField()
#     appointment_end_time = serializers.SerializerMethodField()
#     has_prescription = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Appointment
#         fields = [
#             'id', 'doctor_name', 'doctor_department', 'doctor_profile_image',
#             'appointment_date', 'appointment_time', 'appointment_end_time',
#             'appointment_type', 'medical_history', 'status', 'meeting_link',
#             'has_prescription', 'created_at'
#         ]
    
#     def get_doctor_name(self, obj):
#         return f"Dr. {obj.doctor.user.first_name} {obj.doctor.user.last_name}"
    
#     def get_doctor_department(self, obj):
#         return obj.doctor.department.name if obj.doctor.department else "General"
    
#     def get_doctor_profile_image(self, obj):
#         if obj.doctor.profile_image:
#             img_path = str(obj.doctor.profile_image)
#             if img_path.startswith('media/') or img_path.startswith('/media/'):
#                 return f"/{img_path.lstrip('/')}"
#             return f"/media/{img_path}"
#         return "/static/images/doctors/default.png"
    
#     def get_appointment_date(self, obj):
#         return obj.slot.date.strftime("%d %b, %Y")
    
#     def get_appointment_time(self, obj):
#         return obj.slot.start_time.strftime("%I:%M %p")
    
#     def get_appointment_end_time(self, obj):
#         return obj.slot.end_time.strftime("%I:%M %p")
    
#     def get_has_prescription(self, obj):
#         try:
#             return hasattr(obj, 'prescription')
#         except:
#             return False


# class PrescriptionDetailSerializer(serializers.ModelSerializer):
#     doctor_name = serializers.SerializerMethodField()
#     doctor_qualification = serializers.SerializerMethodField()
#     appointment_date = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Prescription
#         fields = ['id', 'doctor_name', 'doctor_qualification', 'notes', 
#                   'appointment_date', 'created_at']
    
#     def get_doctor_name(self, obj):
#         return f"Dr. {obj.doctor.user.first_name} {obj.doctor.user.last_name}"
    
#     def get_doctor_qualification(self, obj):
#         return f"{obj.doctor.experience}+ Years Experience | {obj.doctor.department.name}"
    
#     def get_appointment_date(self, obj):
#         return obj.appointment.slot.date.strftime("%d %b, %Y")


#######################################################################


#impoertant without dashboard 
# from rest_framework import serializers
# from .models import Doctor, Department, DoctorSchedule

# class DepartmentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Department
#         fields = ['id', 'name', 'description']

# class DoctorScheduleSerializer(serializers.ModelSerializer):
#     # Time ko 09:00 AM format mein dikhane ke liye
#     start_time = serializers.TimeField(format="%I:%M %p")
#     end_time = serializers.TimeField(format="%I:%M %p")
#     day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

#     class Meta:
#         model = DoctorSchedule
#         fields = ['day_of_week', 'day_display', 'start_time', 'end_time', 'is_available']

# class DoctorSerializer(serializers.ModelSerializer):
#     name = serializers.SerializerMethodField()
#     department_name = serializers.CharField(source='department.name', read_only=True)
#     schedules = DoctorScheduleSerializer(many=True, read_only=True)
#     profile_image = serializers.SerializerMethodField()

#     class Meta:
#         model = Doctor
#         fields = ['id', 'name', 'department_name', 'experience', 'consultation_fee', 'profile_image', 'schedules']

#     def get_name(self, obj):
#         return f"Dr. {obj.user.first_name} {obj.user.last_name}"

#     def get_profile_image(self, obj):
#         if obj.profile_image:
#             img_path = str(obj.profile_image)
#             if img_path.startswith('media/') or img_path.startswith('/media/'):
#                 return f"/{img_path.lstrip('/')}"
#             return f"/media/{img_path}"
#         return "/static/images/doctors/default.png"




###################################################
# # from rest_framework import serializers
# # from .models import Doctor, Department, DoctorSchedule

# # class DepartmentSerializer(serializers.ModelSerializer):
# #     class Meta:
# #         model = Department
# #         fields = ['id', 'name', 'description']



# # class DoctorScheduleSerializer(serializers.ModelSerializer):
# #     class Meta:
# #         model = DoctorSchedule
# #         fields = ['day_of_week', 'start_time', 'end_time', 'is_available']

# # class DoctorSerializer(serializers.ModelSerializer):
# #     # User model se name lane ke liye
# #     name = serializers.SerializerMethodField()
# #     department_name = serializers.CharField(source='department.name', read_only=True)
# #     schedules = DoctorScheduleSerializer(many=True, read_only=True)

# #     class Meta:
# #         model = Doctor
# #         fields = ['id', 'name', 'department_name', 'experience', 'consultation_fee', 'profile_image', 'schedules']

# #     def get_name(self, obj):
# #         return f"Dr. {obj.user.first_name} {obj.user.last_name}"        



# # from rest_framework import serializers
# # from .models import Doctor, Department, DoctorSchedule

# # class DepartmentSerializer(serializers.ModelSerializer):
# #     class Meta:
# #         model = Department
# #         fields = ['id', 'name', 'description']

# # class DoctorScheduleSerializer(serializers.ModelSerializer):
# #     class Meta:
# #         model = DoctorSchedule
# #         fields = ['day_of_week', 'start_time', 'end_time', 'is_available']

# # class DoctorSerializer(serializers.ModelSerializer):
# #     name = serializers.SerializerMethodField()
# #     department_name = serializers.CharField(source='department.name', read_only=True)
# #     schedules = DoctorScheduleSerializer(many=True, read_only=True)
# #     profile_image = serializers.SerializerMethodField()

# #     class Meta:
# #         model = Doctor
# #         fields = ['id', 'name', 'department_name', 'experience', 'consultation_fee', 'profile_image', 'schedules']

# #     def get_name(self, obj):
# #         return f"Dr. {obj.user.first_name} {obj.user.last_name}"

# #     def get_profile_image(self, obj):
# #         if obj.profile_image:
# #             img_path = str(obj.profile_image)
# #             # Agar database mein path already 'media/' se start ho raha hai
# #             if img_path.startswith('media/') or img_path.startswith('/media/'):
# #                 return f"/{img_path.lstrip('/')}"
# #             # Normal case
# #             return f"/media/{img_path}"
# #         # Agar image na ho to default image
# #         return "/static/images/doctors/default.png"



# from rest_framework import serializers
# from .models import Doctor, Department, DoctorSchedule

# class DepartmentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Department
#         fields = ['id', 'name', 'description']

# class DoctorScheduleSerializer(serializers.ModelSerializer):
#     # Time ko 09:00 AM format mein dikhane ke liye
#     start_time = serializers.TimeField(format="%I:%M %p")
#     end_time = serializers.TimeField(format="%I:%M %p")
#     day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

#     class Meta:
#         model = DoctorSchedule
#         fields = ['day_of_week', 'day_display', 'start_time', 'end_time', 'is_available']

# class DoctorSerializer(serializers.ModelSerializer):
#     name = serializers.SerializerMethodField()
#     department_name = serializers.CharField(source='department.name', read_only=True)
#     schedules = DoctorScheduleSerializer(many=True, read_only=True)
#     profile_image = serializers.SerializerMethodField()

#     class Meta:
#         model = Doctor
#         fields = ['id', 'name', 'department_name', 'experience', 'consultation_fee', 'profile_image', 'schedules']

#     def get_name(self, obj):
#         return f"Dr. {obj.user.first_name} {obj.user.last_name}"

#     def get_profile_image(self, obj):
#         if obj.profile_image:
#             img_path = str(obj.profile_image)
#             if img_path.startswith('media/') or img_path.startswith('/media/'):
#                 return f"/{img_path.lstrip('/')}"
#             return f"/media/{img_path}"
#         return "/static/images/doctors/default.png"
    

