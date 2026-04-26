import uuid
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import Doctor, Department, DoctorSchedule, TimeSlot, Appointment
from .serializers import DepartmentSerializer, DoctorSerializer

# --- Rendering Views (Pages) ---

def doctor_profile_page_view(request, doc_id):
    """Doctor ki profile page dikhane ke liye"""
    return render(request, 'appointment/doctor_profile.html', {'doc_id': doc_id})

def doctor_list_page_view(request):
    """Saray doctors ki list wala page"""
    return render(request, 'appointment/doctors_list.html')

def booking_page_view(request, doc_id):
    """Booking form jahan user data fill karega"""
    if not request.user.is_authenticated:
        return render(request, 'login.html') 

    doctor = get_object_or_404(Doctor, id=doc_id)
    raw_schedules = list(DoctorSchedule.objects.filter(doctor=doctor, is_available=True))
    
    days_map = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 
        'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    # Schedule kal se dikhana shuru karein
    tomorrow_weekday = (datetime.today() + timedelta(days=1)).weekday()

    def sort_key(sch):
        day_num = days_map[sch.day_of_week.lower()]
        if day_num < tomorrow_weekday:
            return day_num + 7
        return day_num

    sorted_days = sorted(raw_schedules, key=sort_key)

    return render(request, 'appointment/booking_form.html', {
        'doctor': doctor,
        'available_days': sorted_days
    })

# --- API Views ---

class DoctorDetailAPIView(APIView):
    def get(self, request, doc_id):
        try:
            doctor = Doctor.objects.get(id=doc_id)
            return Response(DoctorSerializer(doctor).data)
        except Doctor.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=404)

class DepartmentListView(APIView):
    def get(self, request):
        query = request.query_params.get('search', '').strip()
        departments = Department.objects.all()
        if query:
            departments = departments.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
        return Response(DepartmentSerializer(departments, many=True).data)

class DoctorListView(APIView):
    def get(self, request):
        dept_id = request.query_params.get('dept_id')
        doctors = Doctor.objects.filter(department_id=dept_id) if dept_id else Doctor.objects.all()
        dept_name = Department.objects.get(id=dept_id).name if dept_id else "All Specialists"
        return Response({'department_name': dept_name, 'doctors': DoctorSerializer(doctors, many=True).data})

# --- Booking Logic Helpers ---

def get_next_date_of_day(day_name):
    """Agli aane wali tareekh calculate karne ke liye"""
    days_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
    today = datetime.today().date()
    target_day_num = days_map[day_name.lower()]
    current_day_num = datetime.today().weekday()
    
    days_ahead = target_day_num - current_day_num
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)

@api_view(['GET'])
def get_available_slots_api(request):
    """Slots ko AM/PM format mein frontend bhejne ke liye lekin value 24h rakhi hai"""
    doctor_id = request.GET.get('doctor_id')
    day = request.GET.get('day')
    try:
        schedule = DoctorSchedule.objects.get(doctor_id=doctor_id, day_of_week=day, is_available=True)
        target_date = get_next_date_of_day(day)
        slots = []
        curr = datetime.combine(target_date, schedule.start_time)
        end = datetime.combine(target_date, schedule.end_time)
        
        while curr < end:
            slot_start_24 = curr.time()
            # Display format (AM/PM) for User
            display_time = curr.strftime("%I:%M %p")
            # Raw format (24h) for Backend
            value_time = slot_start_24.strftime("%H:%M")
            
            curr += timedelta(minutes=30)
            
            if not TimeSlot.objects.filter(doctor_id=doctor_id, date=target_date, start_time=slot_start_24, is_booked=True).exists():
                slots.append({
                    "display": display_time,
                    "value": value_time
                })
        
        return JsonResponse({
            'slots': slots, 
            'formatted_date': target_date.strftime("%d-%b-%Y"), 
            'raw_date': target_date.strftime("%Y-%m-%d")
        })
    except DoctorSchedule.DoesNotExist:
        return JsonResponse({'error': 'No schedule found'}, status=404)

# --- MAIN BOOKING API ---

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_appointment_api(request):
    data = request.data
    user = request.user

    try:
        doctor = Doctor.objects.get(id=data['doctor_id'])
        
        # 1. Self-Booking Check
        if doctor.user.id == user.id:
            return JsonResponse({
                'status': 'error',
                'message': 'You cannot book an appointment with yourself.'
            }, status=400)

        # 2. Staff & Superuser Protection Logic
        # Role sirf tab badle ga agar user Superuser na ho aur uska current role 'user' ho
        if not user.is_superuser and user.role == 'user':
            user.role = 'patient'
            user.save()

        # 3. Fee Validation (Double check on backend)
        try:
            paid_amount = float(data.get('paid_amount', 0))
            if paid_amount < float(doctor.consultation_fee):
                return JsonResponse({
                    'status': 'error',
                    'message': f'Insufficient fee. Minimum required is Rs. {doctor.consultation_fee}'
                }, status=400)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid fee amount.'}, status=400)

        booking_date = data['date']
        start_time_str = data['start_time'] # Ye already 24h format mein aayega
        
        # 4. Double Booking Check
        already_booked = Appointment.objects.filter(
            patient=user,
            slot__date=booking_date,
            slot__start_time=start_time_str,
            status='confirmed'
        ).exists()

        if already_booked:
            return JsonResponse({
                'status': 'error',
                'message': 'You already have an appointment at this time with another doctor.'
            }, status=400)

        # 5. Save Data
        start_dt = datetime.strptime(start_time_str, "%H:%M")
        end_time = (start_dt + timedelta(minutes=30)).time()

        slot = TimeSlot.objects.create(
            doctor=doctor, 
            date=booking_date, 
            start_time=start_time_str, 
            end_time=end_time, 
            is_booked=True
        )
        
        meeting_link = f"https://meet.jit.si/CareSync-{uuid.uuid4().hex[:10]}" if data['appointment_type'] == 'online' else ""

        Appointment.objects.create(
            patient=user, 
            doctor=doctor, 
            slot=slot,
            appointment_type=data['appointment_type'],
            medical_history=data.get('medical_history', ''),
            status='confirmed', 
            meeting_link=meeting_link
        )
        
        return JsonResponse({'status': 'success'})

    except Doctor.DoesNotExist:
        return JsonResponse({'message': 'Doctor not found'}, status=404)
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=500)





#time update
# import uuid
# from datetime import datetime, timedelta
# from django.shortcuts import render, get_object_or_404
# from django.http import JsonResponse
# from django.db.models import Q
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated

# from .models import Doctor, Department, DoctorSchedule, TimeSlot, Appointment
# from .serializers import DepartmentSerializer, DoctorSerializer

# # --- Rendering Views (Pages) ---

# def doctor_profile_page_view(request, doc_id):
#     """Doctor ki profile page render karne ke liye"""
#     return render(request, 'appointment/doctor_profile.html', {'doc_id': doc_id})

# def doctor_list_page_view(request):
#     """Doctors ki list wala page render karne ke liye"""
#     return render(request, 'appointment/doctors_list.html')

# def booking_page_view(request, doc_id):
#     """Booking form page dikhane ke liye aur available days sort karne ke liye"""
#     if not request.user.is_authenticated:
#         return render(request, 'login.html') 

#     doctor = get_object_or_404(Doctor, id=doc_id)
#     raw_schedules = list(DoctorSchedule.objects.filter(doctor=doctor, is_available=True))
    
#     days_map = {
#         'monday': 0, 'tuesday': 1, 'wednesday': 2, 
#         'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
#     }
    
#     # Aaj ka din skip karke kal se schedule dikhane ki logic
#     tomorrow_weekday = (datetime.today() + timedelta(days=1)).weekday()

#     def sort_key(sch):
#         day_num = days_map[sch.day_of_week.lower()]
#         if day_num < tomorrow_weekday:
#             return day_num + 7
#         return day_num

#     sorted_days = sorted(raw_schedules, key=sort_key)

#     return render(request, 'appointment/booking_form.html', {
#         'doctor': doctor,
#         'available_days': sorted_days
#     })

# # --- API Views ---

# class DoctorDetailAPIView(APIView):
#     def get(self, request, doc_id):
#         try:
#             doctor = Doctor.objects.get(id=doc_id)
#             return Response(DoctorSerializer(doctor).data)
#         except Doctor.DoesNotExist:
#             return Response({'error': 'Doctor not found'}, status=404)

# class DepartmentListView(APIView):
#     def get(self, request):
#         query = request.query_params.get('search', '').strip()
#         departments = Department.objects.all()
#         if query:
#             departments = departments.filter(
#                 Q(name__icontains=query) | Q(description__icontains=query)
#             )
#         return Response(DepartmentSerializer(departments, many=True).data)

# class DoctorListView(APIView):
#     def get(self, request):
#         dept_id = request.query_params.get('dept_id')
#         doctors = Doctor.objects.filter(department_id=dept_id) if dept_id else Doctor.objects.all()
#         dept_name = Department.objects.get(id=dept_id).name if dept_id else "All Specialists"
#         return Response({'department_name': dept_name, 'doctors': DoctorSerializer(doctors, many=True).data})

# # --- Booking Logic Helpers ---

# def get_next_date_of_day(day_name):
#     """Day name se agli aane wali date calculate karne ke liye"""
#     days_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
#     today = datetime.today().date()
#     target_day_num = days_map[day_name.lower()]
#     current_day_num = datetime.today().weekday()
    
#     days_ahead = target_day_num - current_day_num
#     if days_ahead <= 0:
#         days_ahead += 7
#     return today + timedelta(days=days_ahead)

# @api_view(['GET'])
# def get_available_slots_api(request):
#     """Frontend par slots load karne ke liye API"""
#     doctor_id = request.GET.get('doctor_id')
#     day = request.GET.get('day')
#     try:
#         schedule = DoctorSchedule.objects.get(doctor_id=doctor_id, day_of_week=day, is_available=True)
#         target_date = get_next_date_of_day(day)
#         slots = []
#         curr = datetime.combine(target_date, schedule.start_time)
#         end = datetime.combine(target_date, schedule.end_time)
        
#         while curr < end:
#             slot_start = curr.time()
#             curr += timedelta(minutes=30)
#             if not TimeSlot.objects.filter(doctor_id=doctor_id, date=target_date, start_time=slot_start, is_booked=True).exists():
#                 slots.append({"start": slot_start.strftime("%H:%M")})
        
#         return JsonResponse({
#             'slots': slots, 
#             'formatted_date': target_date.strftime("%d-%b-%Y"), 
#             'raw_date': target_date.strftime("%Y-%m-%d")
#         })
#     except DoctorSchedule.DoesNotExist:
#         return JsonResponse({'error': 'No schedule found'}, status=404)

# # --- MAIN BOOKING API (Updated with Superuser & Staff Logic) ---

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def book_appointment_api(request):
#     data = request.data
#     user = request.user

#     try:
#         doctor = Doctor.objects.get(id=data['doctor_id'])
        
#         # 1. Self-Booking Check: Kya ye wahi banda hai jiski profile hai?
#         if doctor.user.id == user.id:
#             return JsonResponse({
#                 'status': 'error',
#                 'message': 'You cannot book an appointment with yourself.'
#             }, status=400)

#         # 2. Smart Role Update Logic:
#         # Agar user Superuser NAHI hai, aur uska role 'user' hai, sirf tab 'patient' banao.
#         # Is se Admin, Pharmacist, Lab Tech, aur Superuser ka role change nahi hoga.
#         if not user.is_superuser and user.role == 'user':
#             user.role = 'patient'
#             user.save()

#         booking_date = data['date']
#         start_time_str = data['start_time']
        
#         # 3. Double Booking Check (Conflict Management)
#         # Check ke is user ki isi date aur time par koi CONFIRMED appointment to nahi?
#         already_booked = Appointment.objects.filter(
#             patient=user,
#             slot__date=booking_date,
#             slot__start_time=start_time_str,
#             status='confirmed'
#         ).exists()

#         if already_booked:
#             return JsonResponse({
#                 'status': 'error',
#                 'message': 'You already have an appointment at this time with another doctor.'
#             }, status=400)

#         # 4. Finalizing Booking: TimeSlot aur Appointment create karna
#         start_dt = datetime.strptime(start_time_str, "%H:%M")
#         end_time = (start_dt + timedelta(minutes=30)).time()

#         slot = TimeSlot.objects.create(
#             doctor=doctor, 
#             date=booking_date, 
#             start_time=start_time_str, 
#             end_time=end_time, 
#             is_booked=True
#         )
        
#         # Online meeting link agar type 'online' ho
#         meeting_link = f"https://meet.jit.si/CareSync-{uuid.uuid4().hex[:10]}" if data['appointment_type'] == 'online' else ""

#         Appointment.objects.create(
#             patient=user, 
#             doctor=doctor, 
#             slot=slot,
#             appointment_type=data['appointment_type'],
#             medical_history=data.get('medical_history', ''),
#             status='confirmed', 
#             meeting_link=meeting_link
#         )
        
#         return JsonResponse({'status': 'success'})

#     except Doctor.DoesNotExist:
#         return JsonResponse({'message': 'Doctor not found'}, status=404)
#     except Exception as e:
#         return JsonResponse({'message': str(e)}, status=500)
#######################################################
# Anyone not book appoinment miss is ma 
# import uuid
# from datetime import datetime, timedelta
# from django.shortcuts import render, get_object_or_404
# from django.http import JsonResponse
# from django.db.models import Q
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated

# from .models import Doctor, Department, DoctorSchedule, TimeSlot, Appointment
# from .serializers import DepartmentSerializer, DoctorSerializer

# # --- Views for Rendering Pages ---

# def doctor_profile_page_view(request, doc_id):
#     return render(request, 'appointment/doctor_profile.html', {'doc_id': doc_id})

# def doctor_list_page_view(request):
#     return render(request, 'appointment/doctors_list.html')

# def booking_page_view(request, doc_id):
#     if not request.user.is_authenticated:
#         return render(request, 'login.html') 

#     doctor = get_object_or_404(Doctor, id=doc_id)
#     raw_schedules = list(DoctorSchedule.objects.filter(doctor=doctor, is_available=True))
    
#     days_map = {
#         'monday': 0, 'tuesday': 1, 'wednesday': 2, 
#         'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
#     }
    
#     # Aaj ka din skip karke kal se dikhana
#     tomorrow_weekday = (datetime.today() + timedelta(days=1)).weekday()

#     def sort_key(sch):
#         day_num = days_map[sch.day_of_week.lower()]
#         if day_num < tomorrow_weekday:
#             return day_num + 7
#         return day_num

#     sorted_days = sorted(raw_schedules, key=sort_key)

#     return render(request, 'appointment/booking_form.html', {
#         'doctor': doctor,
#         'available_days': sorted_days
#     })

# # --- API Views ---

# class DoctorDetailAPIView(APIView):
#     def get(self, request, doc_id):
#         try:
#             doctor = Doctor.objects.get(id=doc_id)
#             serializer = DoctorSerializer(doctor)
#             return Response(serializer.data)
#         except Doctor.DoesNotExist:
#             return Response({'error': 'Doctor not found'}, status=404)

# class DepartmentListView(APIView):
#     def get(self, request):
#         query = request.query_params.get('search', '').strip()
#         departments = Department.objects.all()
#         if query:
#             departments = departments.filter(
#                 Q(name__icontains=query) | Q(description__icontains=query)
#             )
#         serializer = DepartmentSerializer(departments, many=True)
#         return Response(serializer.data)

# class DoctorListView(APIView):
#     def get(self, request):
#         dept_id = request.query_params.get('dept_id')
#         doctors = Doctor.objects.filter(department_id=dept_id) if dept_id else Doctor.objects.all()
#         dept_name = Department.objects.get(id=dept_id).name if dept_id else "All Specialists"
        
#         serializer = DoctorSerializer(doctors, many=True)
#         return Response({'department_name': dept_name, 'doctors': serializer.data})

# # --- Booking Logic API ---

# def get_next_date_of_day(day_name):
#     days_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
#     today = datetime.today().date()
#     target_day_num = days_map[day_name.lower()]
#     current_day_num = datetime.today().weekday()
    
#     days_ahead = target_day_num - current_day_num
#     if days_ahead <= 0:
#         days_ahead += 7
#     return today + timedelta(days=days_ahead)

# @api_view(['GET'])
# def get_available_slots_api(request):
#     doctor_id = request.GET.get('doctor_id')
#     day = request.GET.get('day')
#     try:
#         schedule = DoctorSchedule.objects.get(doctor_id=doctor_id, day_of_week=day, is_available=True)
#         target_date = get_next_date_of_day(day)
#         slots = []
#         curr = datetime.combine(target_date, schedule.start_time)
#         end = datetime.combine(target_date, schedule.end_time)
        
#         while curr < end:
#             slot_start = curr.time()
#             curr += timedelta(minutes=30)
#             if not TimeSlot.objects.filter(doctor_id=doctor_id, date=target_date, start_time=slot_start, is_booked=True).exists():
#                 slots.append({"start": slot_start.strftime("%H:%M")})
        
#         return JsonResponse({
#             'slots': slots, 
#             'formatted_date': target_date.strftime("%d-%b-%Y"), 
#             'raw_date': target_date.strftime("%Y-%m-%d")
#         })
#     except DoctorSchedule.DoesNotExist:
#         return JsonResponse({'error': 'No schedule found'}, status=404)

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def book_appointment_api(request):
#     data = request.data
#     user = request.user

#     # 1. Role Update Logic
#     if user.role == 'user':
#         user.role = 'patient'
#         user.save()
    
#     if user.role != 'patient':
#         return JsonResponse({'message': 'Only patients can book appointments.'}, status=403)

#     try:
#         doctor = Doctor.objects.get(id=data['doctor_id'])
#         booking_date = data['date']
#         start_time_str = data['start_time']
        
#         # 2. Double Booking Check (Same user, same time, another doctor)
#         already_booked = Appointment.objects.filter(
#             patient=user,
#             slot__date=booking_date,
#             slot__start_time=start_time_str,
#             status='confirmed'
#         ).exists()

#         if already_booked:
#             return JsonResponse({
#                 'status': 'error',
#                 'message': 'You already have an appointment at this time with another doctor.'
#             }, status=400)

#         # 3. TimeSlot & Appointment Creation
#         start_dt = datetime.strptime(start_time_str, "%H:%M")
#         end_time = (start_dt + timedelta(minutes=30)).time()

#         slot = TimeSlot.objects.create(
#             doctor=doctor, date=booking_date, start_time=start_time_str, 
#             end_time=end_time, is_booked=True
#         )
        
#         meeting_link = f"https://meet.jit.si/CareSync-{uuid.uuid4().hex[:10]}" if data['appointment_type'] == 'online' else ""

#         Appointment.objects.create(
#             patient=user, doctor=doctor, slot=slot,
#             appointment_type=data['appointment_type'],
#             medical_history=data.get('medical_history', ''),
#             status='confirmed', meeting_link=meeting_link
#         )
        
#         return JsonResponse({'status': 'success'})
#     except Exception as e:
#         return JsonResponse({'message': str(e)}, status=500)


#################
#here validation miss do departemnet check wali 
# # import uuid
# # from datetime import datetime, timedelta
# # from django.shortcuts import render, get_object_or_404
# # from django.http import JsonResponse
# # from django.db.models import Q
# # from rest_framework.views import APIView
# # from rest_framework.response import Response
# # from rest_framework.decorators import api_view, permission_classes
# # from rest_framework.permissions import IsAuthenticated

# # from .models import Doctor, Department, DoctorSchedule, TimeSlot, Appointment
# # from .serializers import DepartmentSerializer, DoctorSerializer

# # # --- Existing Views ---

# # def doctor_profile_page_view(request, doc_id):
# #     return render(request, 'appointment/doctor_profile.html', {'doc_id': doc_id})

# # def doctor_list_page_view(request):
# #     return render(request, 'appointment/doctors_list.html')

# # class DoctorDetailAPIView(APIView):
# #     def get(self, request, doc_id):
# #         try:
# #             doctor = Doctor.objects.get(id=doc_id)
# #             serializer = DoctorSerializer(doctor)
# #             return Response(serializer.data)
# #         except Doctor.DoesNotExist:
# #             return Response({'error': 'Doctor not found'}, status=404)

# # class DepartmentListView(APIView):
# #     def get(self, request):
# #         query = request.query_params.get('search', '').strip()
# #         departments = Department.objects.all()
# #         if query:
# #             departments = departments.filter(
# #                 Q(name__icontains=query) | Q(description__icontains=query)
# #             )
# #         serializer = DepartmentSerializer(departments, many=True)
# #         return Response(serializer.data)

# # class DoctorListView(APIView):
# #     def get(self, request):
# #         dept_id = request.query_params.get('dept_id')
# #         if dept_id:
# #             doctors = Doctor.objects.filter(department_id=dept_id)
# #             dept = Department.objects.get(id=dept_id)
# #             dept_name = dept.name
# #         else:
# #             doctors = Doctor.objects.all()
# #             dept_name = "All Specialists"
# #         serializer = DoctorSerializer(doctors, many=True)
# #         return Response({
# #             'department_name': dept_name,
# #             'doctors': serializer.data
# #         })

# # # --- Final Booking Logic (Today Skipped, Next 7 Days Sorted) ---

# # def booking_page_view(request, doc_id):
# #     # Ensure user is logged in before seeing the form
# #     if not request.user.is_authenticated:
# #         return render(request, 'login.html') 

# #     doctor = get_object_or_404(Doctor, id=doc_id)
    
# #     # 1. Doctor ke available days
# #     raw_schedules = list(DoctorSchedule.objects.filter(doctor=doctor, is_available=True))
    
# #     days_map = {
# #         'monday': 0, 'tuesday': 1, 'wednesday': 2, 
# #         'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
# #     }
    
# #     # 2. Aaj ka din skip karke "Kal" (Tomorrow) se logic shuru karni hai
# #     tomorrow_weekday = (datetime.today() + timedelta(days=1)).weekday()

# #     def sort_key(sch):
# #         day_num = days_map[sch.day_of_week.lower()]
# #         if day_num < tomorrow_weekday:
# #             return day_num + 7
# #         return day_num

# #     # 3. Days ko "Kal" ki date ke mutabiq sort karein
# #     sorted_days = sorted(raw_schedules, key=sort_key)

# #     return render(request, 'appointment/booking_form.html', {
# #         'doctor': doctor,
# #         'available_days': sorted_days
# #     })

# # def get_next_date_of_day(day_name):
# #     days_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
# #     today = datetime.today().date()
# #     target_day_num = days_map[day_name.lower()]
    
# #     current_day_num = datetime.today().weekday()
# #     days_ahead = target_day_num - current_day_num
    
# #     # Always move to next occurrence if it's today or in the past
# #     if days_ahead <= 0:
# #         days_ahead += 7
        
# #     return today + timedelta(days=days_ahead)

# # @api_view(['GET'])
# # def get_available_slots_api(request):
# #     doctor_id = request.GET.get('doctor_id')
# #     day = request.GET.get('day')
    
# #     try:
# #         schedule = DoctorSchedule.objects.get(doctor_id=doctor_id, day_of_week=day, is_available=True)
# #         target_date = get_next_date_of_day(day)
        
# #         slots = []
# #         curr = datetime.combine(target_date, schedule.start_time)
# #         end = datetime.combine(target_date, schedule.end_time)
        
# #         while curr < end:
# #             slot_start = curr.time()
# #             curr += timedelta(minutes=30)
            
# #             is_booked = TimeSlot.objects.filter(
# #                 doctor_id=doctor_id, date=target_date, 
# #                 start_time=slot_start, is_booked=True
# #             ).exists()
            
# #             if not is_booked:
# #                 slots.append({"start": slot_start.strftime("%H:%M")})
        
# #         return JsonResponse({
# #             'slots': slots, 
# #             'formatted_date': target_date.strftime("%d-%b-%Y"), 
# #             'raw_date': target_date.strftime("%Y-%m-%d")
# #         })
# #     except DoctorSchedule.DoesNotExist:
# #         return JsonResponse({'error': 'No schedule found'}, status=404)

# # @api_view(['POST'])
# # @permission_classes([IsAuthenticated])
# # def book_appointment_api(request):
# #     data = request.data
# #     user = request.user

# #     # --- Role Update Logic ---
# #     # Agar user hai to patient bana do
# #     if user.role == 'user':
# #         user.role = 'patient'
# #         user.save()
    
# #     # Role safety check (Sirf patients hi appointment book kar saken)
# #     if user.role != 'patient':
# #         return JsonResponse({'error': 'Only patients can book appointments.'}, status=403)

# #     try:
# #         doctor = Doctor.objects.get(id=data['doctor_id'])
        
# #         # Calculate end time
# #         start_dt = datetime.strptime(data['start_time'], "%H:%M")
# #         end_time = (start_dt + timedelta(minutes=30)).time()

# #         # 1. Create TimeSlot
# #         slot = TimeSlot.objects.create(
# #             doctor=doctor,
# #             date=data['date'],
# #             start_time=data['start_time'],
# #             end_time=end_time,
# #             is_booked=True
# #         )
        
# #         # 2. Meeting link for online
# #         meeting_link = ""
# #         if data['appointment_type'] == 'online':
# #             meeting_link = f"https://meet.jit.si/CareSync-{uuid.uuid4().hex[:10]}"

# #         # 3. Create Appointment
# #         Appointment.objects.create(
# #             patient=user,
# #             doctor=doctor,
# #             slot=slot,
# #             appointment_type=data['appointment_type'],
# #             medical_history=data.get('medical_history', ''),
# #             status='confirmed',
# #             meeting_link=meeting_link
# #         )
        
# #         return JsonResponse({'status': 'success'})
    
# #     except Doctor.DoesNotExist:
# #         return JsonResponse({'error': 'Doctor not found'}, status=404)
# #     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)


#########################################
# import uuid
# from datetime import datetime, timedelta
# from django.shortcuts import render, get_object_or_404
# from django.http import JsonResponse
# from django.db.models import Q
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.decorators import api_view

# from .models import Doctor, Department, DoctorSchedule, TimeSlot, Appointment
# from .serializers import DepartmentSerializer, DoctorSerializer

# # --- Existing Views ---

# def doctor_profile_page_view(request, doc_id):
#     return render(request, 'appointment/doctor_profile.html', {'doc_id': doc_id})

# def doctor_list_page_view(request):
#     return render(request, 'appointment/doctors_list.html')

# class DoctorDetailAPIView(APIView):
#     def get(self, request, doc_id):
#         try:
#             doctor = Doctor.objects.get(id=doc_id)
#             serializer = DoctorSerializer(doctor)
#             return Response(serializer.data)
#         except Doctor.DoesNotExist:
#             return Response({'error': 'Doctor not found'}, status=404)

# class DepartmentListView(APIView):
#     def get(self, request):
#         query = request.query_params.get('search', '').strip()
#         departments = Department.objects.all()
#         if query:
#             departments = departments.filter(
#                 Q(name__icontains=query) | Q(description__icontains=query)
#             )
#         serializer = DepartmentSerializer(departments, many=True)
#         return Response(serializer.data)

# class DoctorListView(APIView):
#     def get(self, request):
#         dept_id = request.query_params.get('dept_id')
#         if dept_id:
#             doctors = Doctor.objects.filter(department_id=dept_id)
#             dept = Department.objects.get(id=dept_id)
#             dept_name = dept.name
#         else:
#             doctors = Doctor.objects.all()
#             dept_name = "All Specialists"
#         serializer = DoctorSerializer(doctors, many=True)
#         return Response({
#             'department_name': dept_name,
#             'doctors': serializer.data
#         })

# # --- Final Booking Logic (Today Skipped, Next 7 Days Sorted) ---

# def booking_page_view(request, doc_id):
#     doctor = get_object_or_404(Doctor, id=doc_id)
    
#     # 1. Doctor ke available days
#     raw_schedules = list(DoctorSchedule.objects.filter(doctor=doctor, is_available=True))
    
#     days_map = {
#         'monday': 0, 'tuesday': 1, 'wednesday': 2, 
#         'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
#     }
    
#     # 2. Aaj ka din skip karke "Kal" (Tomorrow) se logic shuru karni hai
#     tomorrow_weekday = (datetime.today() + timedelta(days=1)).weekday()

#     def sort_key(sch):
#         day_num = days_map[sch.day_of_week.lower()]
#         # Agar day_num kal se chota hai, to iska matlab wo agle hafte aayega (+7)
#         if day_num < tomorrow_weekday:
#             return day_num + 7
#         return day_num

#     # 3. Days ko "Kal" ki date ke mutabiq sort karein
#     sorted_days = sorted(raw_schedules, key=sort_key)

#     return render(request, 'appointment/booking_form.html', {
#         'doctor': doctor,
#         'available_days': sorted_days
#     })

# def get_next_date_of_day(day_name):
#     days_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
#     today = datetime.today().date()
#     target_day_num = days_map[day_name.lower()]
    
#     # Current day number (e.g. Saturday = 5)
#     current_day_num = datetime.today().weekday()
    
#     # Difference nikaalein
#     days_ahead = target_day_num - current_day_num
    
#     # Agar difference 0 hai (yani aaj ka hi din select hua) ya minus mein hai, 
#     # to +7 karke agle hafte ki date dein
#     if days_ahead <= 0:
#         days_ahead += 7
        
#     return today + timedelta(days=days_ahead)

# @api_view(['GET'])
# def get_available_slots_api(request):
#     doctor_id = request.GET.get('doctor_id')
#     day = request.GET.get('day')
    
#     try:
#         schedule = DoctorSchedule.objects.get(doctor_id=doctor_id, day_of_week=day, is_available=True)
#         target_date = get_next_date_of_day(day)
        
#         slots = []
#         curr = datetime.combine(target_date, schedule.start_time)
#         end = datetime.combine(target_date, schedule.end_time)
        
#         while curr < end:
#             slot_start = curr.time()
#             curr += timedelta(minutes=30)
            
#             is_booked = TimeSlot.objects.filter(
#                 doctor_id=doctor_id, date=target_date, 
#                 start_time=slot_start, is_booked=True
#             ).exists()
            
#             if not is_booked:
#                 slots.append({"start": slot_start.strftime("%H:%M")})
        
#         return JsonResponse({
#             'slots': slots, 
#             'formatted_date': target_date.strftime("%d-%b-%Y"), 
#             'raw_date': target_date.strftime("%Y-%m-%d")
#         })
#     except DoctorSchedule.DoesNotExist:
#         return JsonResponse({'error': 'No schedule found'}, status=404)

# @api_view(['POST'])
# def book_appointment_api(request):
#     data = request.data
#     doctor = Doctor.objects.get(id=data['doctor_id'])
    
#     start_dt = datetime.strptime(data['start_time'], "%H:%M")
#     end_time = (start_dt + timedelta(minutes=30)).time()

#     slot = TimeSlot.objects.create(
#         doctor=doctor,
#         date=data['date'],
#         start_time=data['start_time'],
#         end_time=end_time,
#         is_booked=True
#     )
    
#     meeting_link = ""
#     if data['appointment_type'] == 'online':
#         meeting_link = f"https://meet.jit.si/CareSync-{uuid.uuid4().hex[:10]}"

#     Appointment.objects.create(
#         patient=request.user,
#         doctor=doctor,
#         slot=slot,
#         appointment_type=data['appointment_type'],
#         medical_history=data.get('medical_history', ''),
#         status='confirmed',
#         meeting_link=meeting_link
#     )
    
#     return JsonResponse({'status': 'success'})


#############################################
# import uuid
# from datetime import datetime, timedelta
# from django.shortcuts import render, get_object_or_404
# from django.http import JsonResponse
# from django.db.models import Q
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.decorators import api_view
# from .models import Doctor, Department, DoctorSchedule, TimeSlot, Appointment
# from .serializers import DepartmentSerializer, DoctorSerializer

# # --- Existing Views ---

# def doctor_profile_page_view(request, doc_id):
#     return render(request, 'appointment/doctor_profile.html', {'doc_id': doc_id})

# def doctor_list_page_view(request):
#     return render(request, 'appointment/doctors_list.html')

# class DoctorDetailAPIView(APIView):
#     def get(self, request, doc_id):
#         try:
#             doctor = Doctor.objects.get(id=doc_id)
#             serializer = DoctorSerializer(doctor)
#             return Response(serializer.data)
#         except Doctor.DoesNotExist:
#             return Response({'error': 'Doctor not found'}, status=404)

# class DepartmentListView(APIView):
#     def get(self, request):
#         query = request.query_params.get('search', '').strip()
#         departments = Department.objects.all()
#         if query:
#             departments = departments.filter(
#                 Q(name__icontains=query) | Q(description__icontains=query)
#             )
#         serializer = DepartmentSerializer(departments, many=True)
#         return Response(serializer.data)

# class DoctorListView(APIView):
#     def get(self, request):
#         dept_id = request.query_params.get('dept_id')
#         if dept_id:
#             doctors = Doctor.objects.filter(department_id=dept_id)
#             dept = Department.objects.get(id=dept_id)
#             dept_name = dept.name
#         else:
#             doctors = Doctor.objects.all()
#             dept_name = "All Specialists"
#         serializer = DoctorSerializer(doctors, many=True)
#         return Response({
#             'department_name': dept_name,
#             'doctors': serializer.data
#         })

# # --- New Booking Logic Views ---

# def booking_page_view(request, doc_id):
#     doctor = get_object_or_404(Doctor, id=doc_id)
#     # Sirf wahi days dikhayenge jo schedule mein active hain
#     available_days = DoctorSchedule.objects.filter(doctor=doctor, is_available=True)
#     return render(request, 'appointment/booking_form.html', {
#         'doctor': doctor,
#         'available_days': available_days
#     })

# def get_next_date_of_day(day_name):
#     days_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
#     today = datetime.today()
#     target_day = days_map[day_name.lower()]
#     days_ahead = target_day - today.weekday()
#     if days_ahead <= 0: days_ahead += 7
#     return (today + timedelta(days=days_ahead)).date()

# @api_view(['GET'])
# def get_available_slots_api(request):
#     doctor_id = request.GET.get('doctor_id')
#     day = request.GET.get('day')
    
#     try:
#         schedule = DoctorSchedule.objects.get(doctor_id=doctor_id, day_of_week=day, is_available=True)
#         target_date = get_next_date_of_day(day)
        
#         slots = []
#         curr = datetime.combine(target_date, schedule.start_time)
#         end = datetime.combine(target_date, schedule.end_time)
        
#         while curr < end:
#             slot_start = curr.time()
#             curr += timedelta(minutes=30)
#             slot_end = curr.time()
            
#             # Check if booked
#             is_booked = TimeSlot.objects.filter(
#                 doctor_id=doctor_id, date=target_date, 
#                 start_time=slot_start, is_booked=True
#             ).exists()
            
#             if not is_booked:
#                 slots.append({"start": slot_start.strftime("%H:%M")})
        
#         return JsonResponse({
#             'slots': slots, 
#             'formatted_date': target_date.strftime("%d-%b-%Y"), 
#             'raw_date': target_date.strftime("%Y-%m-%d")
#         })
#     except DoctorSchedule.DoesNotExist:
#         return JsonResponse({'error': 'No schedule found'}, status=404)

# @api_view(['POST'])
# def book_appointment_api(request):
#     data = request.data
#     doctor = Doctor.objects.get(id=data['doctor_id'])
    
#     # Calculate end time (start + 30 mins)
#     start_dt = datetime.strptime(data['start_time'], "%H:%M")
#     end_time = (start_dt + timedelta(minutes=30)).time()

#     # 1. Create TimeSlot
#     slot = TimeSlot.objects.create(
#         doctor=doctor,
#         date=data['date'],
#         start_time=data['start_time'],
#         end_time=end_time,
#         is_booked=True
#     )
    
#     # 2. Link generation (Jitsi)
#     meeting_link = ""
#     if data['appointment_type'] == 'online':
#         meeting_link = f"https://meet.jit.si/CareSync-{uuid.uuid4().hex[:10]}"

#     # 3. Save Appointment (Status confirmed by default)
#     Appointment.objects.create(
#         patient=request.user,
#         doctor=doctor,
#         slot=slot,
#         appointment_type=data['appointment_type'],
#         medical_history=data.get('medical_history', ''),
#         status='confirmed',
#         meeting_link=meeting_link
#     )
    
#     return JsonResponse({'status': 'success'})







##################################################################
# from django.shortcuts import render

# # Create your views here.
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from django.db.models import Q
# from .models import Doctor, Department
# from .serializers import DepartmentSerializer , DoctorSerializer

# # Page View: Sirf HTML render karta hai
# def doctor_profile_page_view(request, doc_id):
#     return render(request, 'appointment/doctor_profile.html', {'doc_id': doc_id})


# # Yeh aapki views.py mein hona lazmi hai
# class DoctorDetailAPIView(APIView):
#     def get(self, request, doc_id):
#         try:
#             doctor = Doctor.objects.get(id=doc_id)
#             serializer = DoctorSerializer(doctor)
#             return Response(serializer.data)
#         except Doctor.DoesNotExist:
#             return Response({'error': 'Doctor not found'}, status=404)
        
# class DepartmentListView(APIView):
#     def get(self, request):
#         query = request.query_params.get('search', '').strip()
#         departments = Department.objects.all()

#         if query:
#             departments = departments.filter(
#                 Q(name__icontains=query) | Q(description__icontains=query)
#             )

#         serializer = DepartmentSerializer(departments, many=True)
#         return Response(serializer.data)
    

# class DoctorListView(APIView):
#     def get(self, request):
#         dept_id = request.query_params.get('dept_id')
#         if dept_id:
#             # Filter doctors by the department clicked
#             doctors = Doctor.objects.filter(department_id=dept_id)
#             dept = Department.objects.get(id=dept_id)
#             dept_name = dept.name
#         else:
#             doctors = Doctor.objects.all()
#             dept_name = "All Specialists"

#         serializer = DoctorSerializer(doctors, many=True)
#         return Response({
#             'department_name': dept_name,
#             'doctors': serializer.data
#         })    
    



# def doctor_list_page_view(request):
#     return render(request, 'appointment/doctors_list.html') # Check karein ke file name sahi ho    