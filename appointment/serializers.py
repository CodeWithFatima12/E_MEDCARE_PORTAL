from rest_framework import serializers
from .models import Doctor, Department, DoctorSchedule

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
    

