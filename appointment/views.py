


#missing name,age,gender 
import uuid
from datetime import datetime, timedelta, date
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import models

from .models import Doctor, Department, DoctorSchedule, TimeSlot, Appointment, Prescription
from .serializers import (
    DepartmentSerializer, DoctorSerializer, PatientAppointmentSerializer, 
    PrescriptionDetailSerializer, DoctorAppointmentSerializer, DoctorScheduleUpdateSerializer, DoctorScheduleSerializer
)


# ==================== RENDERING VIEWS ====================

def doctor_profile_page_view(request, doc_id):
    return render(request, 'appointment/doctor_profile.html', {'doc_id': doc_id})

def doctor_list_page_view(request):
    return render(request, 'appointment/doctors_list.html')

def booking_page_view(request, doc_id):
    if not request.user.is_authenticated:
        return render(request, 'accounts/signin.html')
    
    doctor = get_object_or_404(Doctor, id=doc_id)
    raw_schedules = list(DoctorSchedule.objects.filter(doctor=doctor, is_available=True))
    
    days_map = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 
        'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    today_weekday = datetime.today().weekday()

    def sort_key(sch):
        day_num = days_map[sch.day_of_week.lower()]
        if day_num < today_weekday:
            return day_num + 7
        return day_num

    sorted_days = sorted(raw_schedules, key=sort_key)

    return render(request, 'appointment/booking_form.html', {
        'doctor': doctor,
        'available_days': sorted_days
    })


# ==================== API VIEWS ====================

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


# ==================== BOOKING HELPERS ====================

def get_next_date_of_day(day_name):
    days_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
    today = datetime.today().date()
    target_day_num = days_map[day_name.lower()]
    current_day_num = datetime.today().weekday()
    
    days_ahead = target_day_num - current_day_num
    if days_ahead < 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


@api_view(['GET'])
def get_available_slots_api(request):
    doctor_id = request.GET.get('doctor_id')
    day = request.GET.get('day')
    try:
        schedule = DoctorSchedule.objects.get(doctor_id=doctor_id, day_of_week=day, is_available=True)
        target_date = get_next_date_of_day(day)
        
        now = datetime.now()
        is_today = (target_date == now.date())
        
        #  30 MINUTE BUFFER - Booking process ke liye time
        buffer_time = now + timedelta(minutes=30)
        
        slots = []
        curr = datetime.combine(target_date, schedule.start_time)
        end = datetime.combine(target_date, schedule.end_time)
        
        while curr < end:
            slot_start_24 = curr.time()
            display_time = curr.strftime("%I:%M %p")
            value_time = slot_start_24.strftime("%H:%M")
            
            #  SKIP LOGIC: Buffer time se pehle ke slots skip
            if is_today and curr <= buffer_time:
                curr += timedelta(minutes=30)
                continue
            
            curr += timedelta(minutes=30)
            
            # Check if slot is already booked
            if not TimeSlot.objects.filter(doctor_id=doctor_id, date=target_date, start_time=slot_start_24, is_booked=True).exists():
                slots.append({"display": display_time, "value": value_time})
        
        return JsonResponse({
            'slots': slots, 
            'formatted_date': target_date.strftime("%d-%b-%Y"), 
            'raw_date': target_date.strftime("%Y-%m-%d")
        })
    except DoctorSchedule.DoesNotExist:
        return JsonResponse({'error': 'No schedule found'}, status=404)
# ==================== MAIN BOOKING API ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_appointment_api(request):
    data = request.data
    user = request.user

    try:
        doctor = Doctor.objects.get(id=data['doctor_id'])
        
        if doctor.user.id == user.id:
            return JsonResponse({'status': 'error', 'message': 'You cannot book an appointment with yourself.'}, status=400)

        if not user.is_superuser and hasattr(user, 'role') and user.role == 'user':
            user.role = 'patient'
            user.save()

        try:
            paid_amount = float(data.get('paid_amount', 0))
            if paid_amount < float(doctor.consultation_fee):
                return JsonResponse({'status': 'error', 'message': f'Insufficient fee. Minimum required is Rs. {doctor.consultation_fee}'}, status=400)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid fee amount.'}, status=400)

        booking_date = data['date']
        start_time_str = data['start_time']
        
        already_booked = Appointment.objects.filter(
            patient=user, slot__date=booking_date, slot__start_time=start_time_str, status='confirmed'
        ).exists()

        if already_booked:
            return JsonResponse({'status': 'error', 'message': 'You already have an appointment at this time.'}, status=400)

        start_dt = datetime.strptime(start_time_str, "%H:%M")
        end_time = (start_dt + timedelta(minutes=30)).time()

        slot = TimeSlot.objects.create(
            doctor=doctor, date=booking_date, start_time=start_time_str, end_time=end_time, is_booked=True
        )
        
        meeting_link = f"https://meet.jit.si/CareSync-{uuid.uuid4().hex[:10]}" if data['appointment_type'] == 'online' else ""

        Appointment.objects.create(
            patient=user, doctor=doctor, slot=slot,
            appointment_type=data['appointment_type'],
            medical_history=data.get('medical_history', ''),
            status='confirmed', meeting_link=meeting_link,
            # NEW FIELDS - Form se aayenge
            patient_name=data.get('patient_name', ''),
            phone_number=data.get('phone_number', ''),
            age=data.get('age'),
            gender=data.get('gender', '')
        )
        
        return JsonResponse({'status': 'success'})

    except Doctor.DoesNotExist:
        return JsonResponse({'message': 'Doctor not found'}, status=404)
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=500)


# ==================== PATIENT DASHBOARD VIEWS ====================

def patient_dashboard_view(request):
    if not request.user.is_authenticated:
        return render(request, 'accounts/signin.html')
    return render(request, 'appointment/patient_dashboard.html')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_patient_appointments_api(request):
    user = request.user
    today = date.today()
    
    fresh_appointments = Appointment.objects.filter(
        patient=user, slot__date__gte=today
    ).exclude(status='cancelled').select_related('doctor', 'doctor__user', 'doctor__department', 'slot').order_by('slot__date', 'slot__start_time')
    
    # ✅ FIXED: Sirf Today + Future ki cancelled appointments
    cancelled_appointments = Appointment.objects.filter(
        patient=user, 
        status='cancelled',
        slot__date__gte=today  # ← YEH LINE ADD KARI
    ).select_related('doctor', 'doctor__user', 'doctor__department', 'slot').order_by('slot__date', 'slot__start_time')  # ← order_by bhi change kiya
    
    return Response({
        'fresh_appointments': PatientAppointmentSerializer(fresh_appointments, many=True).data,
        'cancelled_appointments': PatientAppointmentSerializer(cancelled_appointments, many=True).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_appointment_api(request, appointment_id):
    user = request.user
    today = date.today()
    
    try:
        appointment = Appointment.objects.get(id=appointment_id, patient=user)
        
        if appointment.status == 'cancelled':
            return Response({'status': 'error', 'message': 'Already cancelled.'}, status=400)
        
        if appointment.slot.date < today:
            return Response({'status': 'error', 'message': 'Cannot cancel past appointments.'}, status=400)
        
        appointment.slot.is_booked = False
        appointment.slot.save()
        appointment.status = 'cancelled'
        appointment.save()
        
        return Response({'status': 'success', 'message': 'Appointment cancelled successfully.'})
        
    except Appointment.DoesNotExist:
        return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_appointment_slip_api(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id, patient=request.user)
        return Response(PatientAppointmentSerializer(appointment).data)
    except Appointment.DoesNotExist:
        return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_prescription_api(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id, patient=request.user)
        
        if appointment.appointment_type != 'online':
            return Response({'status': 'error', 'message': 'Prescription only for online consultations.'}, status=400)
        
        prescription = Prescription.objects.get(appointment=appointment)
        return Response(PrescriptionDetailSerializer(prescription).data)
    except Appointment.DoesNotExist:
        return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)
    except Prescription.DoesNotExist:
        return Response({'status': 'error', 'message': 'No prescription added yet.'}, status=404)


# ==================== DOCTOR DASHBOARD VIEWS ====================

def doctor_dashboard_view(request):
    """Doctor Dashboard Page"""
    if not request.user.is_authenticated:
        return render(request, 'accounts/signin.html')
    
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return render(request, 'error.html', {'message': 'You are not registered as a doctor.'})
    
    return render(request, 'appointment/doctor_dashboard.html', {'doctor': doctor})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_appointments_api(request):
    """Get doctor's appointments"""
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)
    
    today = date.today()
    
    fresh_appointments = Appointment.objects.filter(
        doctor=doctor, slot__date__gte=today
    ).exclude(status='cancelled').select_related('patient', 'slot').order_by('slot__date', 'slot__start_time')
    
    # ✅ FIXED: Sirf Today + Future ki cancelled appointments
    cancelled_appointments = Appointment.objects.filter(
        doctor=doctor, 
        status='cancelled',
        slot__date__gte=today  # ← YEH LINE ADD KARI
    ).select_related('patient', 'slot').order_by('slot__date', 'slot__start_time')  # ← order_by bhi change kiya
    
    return Response({
        'fresh_appointments': DoctorAppointmentSerializer(fresh_appointments, many=True).data,
        'cancelled_appointments': DoctorAppointmentSerializer(cancelled_appointments, many=True).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_prescription_api(request, appointment_id):
    """Add prescription for online appointment"""
    try:
        doctor = Doctor.objects.get(user=request.user)
        appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)
        
        if appointment.appointment_type != 'online':
            return Response({'status': 'error', 'message': 'Prescriptions can only be added for online appointments.'}, status=400)
        
        if Prescription.objects.filter(appointment=appointment).exists():
            return Response({'status': 'error', 'message': 'Prescription already added for this appointment.'}, status=400)
        
        notes = request.data.get('notes', '').strip()
        if not notes:
            return Response({'status': 'error', 'message': 'Prescription notes are required.'}, status=400)
        
        prescription = Prescription.objects.create(
            appointment=appointment,
            doctor=doctor,
            patient=appointment.patient,
            notes=notes
        )
        
        return Response({
            'status': 'success',
            'message': 'Prescription added successfully.',
            'prescription': PrescriptionDetailSerializer(prescription).data
        })
        
    except Doctor.DoesNotExist:
        return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)
    except Appointment.DoesNotExist:
        return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_schedules_api(request):
    """Get doctor's current schedules"""
    try:
        doctor = Doctor.objects.get(user=request.user)
        schedules = DoctorSchedule.objects.filter(doctor=doctor).order_by(
            models.Case(
                models.When(day_of_week='monday', then=0),
                models.When(day_of_week='tuesday', then=1),
                models.When(day_of_week='wednesday', then=2),
                models.When(day_of_week='thursday', then=3),
                models.When(day_of_week='friday', then=4),
                models.When(day_of_week='saturday', then=5),
                models.When(day_of_week='sunday', then=6),
                default=7,
            )
        )
        return Response(DoctorScheduleSerializer(schedules, many=True).data)
    except Doctor.DoesNotExist:
        return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_doctor_schedule_api(request):
    """Update doctor's schedule - handles cancellations if schedule changes"""
    try:
        doctor = Doctor.objects.get(user=request.user)
        schedule_data = request.data.get('schedules', [])
        
        for item in schedule_data:
            day = item.get('day_of_week')
            start_time = item.get('start_time')
            end_time = item.get('end_time')
            is_available = item.get('is_available', True)
            
            if not day:
                continue
            
            schedule, created = DoctorSchedule.objects.get_or_create(
                doctor=doctor,
                day_of_week=day,
                defaults={
                    'start_time': start_time,
                    'end_time': end_time,
                    'is_available': is_available
                }
            )
            
            if not created:
                old_start = schedule.start_time
                old_end = schedule.end_time
                old_available = schedule.is_available
                
                schedule.start_time = start_time
                schedule.end_time = end_time
                schedule.is_available = is_available
                schedule.save()
                
                if not is_available or old_start != start_time or old_end != end_time:
                    cancel_affected_appointments(doctor, day, old_start, old_end, start_time, end_time, is_available)
        
        return Response({'status': 'success', 'message': 'Schedule updated successfully.'})
        
    except Doctor.DoesNotExist:
        return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)

def cancel_affected_appointments(doctor, day_of_week, old_start, old_end, new_start, new_end, is_available):
    """Cancel appointments that are no longer within working hours"""
    days_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
    target_weekday = days_map.get(day_of_week.lower())
    
    if target_weekday is None:
        return
    
    today = date.today()
    current_date = today
    while current_date.weekday() != target_weekday:
        current_date += timedelta(days=1)
    
    for i in range(90):
        appointment_date = current_date + timedelta(days=i*7)
        
        if not is_available:
            appointments = Appointment.objects.filter(
                doctor=doctor, slot__date=appointment_date, status='confirmed'
            )
        else:
            appointments = Appointment.objects.filter(
                doctor=doctor, slot__date=appointment_date, slot__start_time__lt=new_start, status='confirmed'
            ) | Appointment.objects.filter(
                doctor=doctor, slot__date=appointment_date, slot__end_time__gt=new_end, status='confirmed'
            )
        
        for appointment in appointments:
            slot = appointment.slot
            slot.is_booked = False
            slot.save()
            appointment.status = 'cancelled'
            appointment.save()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_appointment_detail_api(request, appointment_id):
    """Get single appointment detail for prescription"""
    try:
        doctor = Doctor.objects.get(user=request.user)
        appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)
        return Response(DoctorAppointmentSerializer(appointment).data)
    except Doctor.DoesNotExist:
        return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)
    except Appointment.DoesNotExist:
        return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_prescription_api(request, appointment_id):
    """Get prescription for an appointment (for doctor view)"""
    try:
        doctor = Doctor.objects.get(user=request.user)
        appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)
        
        try:
            prescription = Prescription.objects.get(appointment=appointment)
            serializer = PrescriptionDetailSerializer(prescription)
            return Response(serializer.data)
        except Prescription.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'No prescription added yet for this appointment.'
            }, status=404)
        
    except Doctor.DoesNotExist:
        return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)
    except Appointment.DoesNotExist:
        return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)


# ==================== DOCTOR CANCEL APPOINTMENT API ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def doctor_cancel_appointment_api(request, appointment_id):
    """Doctor cancels an appointment"""
    try:
        doctor = Doctor.objects.get(user=request.user)
        appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)
        
        if appointment.status == 'cancelled':
            return Response({
                'status': 'error',
                'message': 'This appointment is already cancelled.'
            }, status=400)
        
        if appointment.status != 'confirmed':
            return Response({
                'status': 'error',
                'message': f'Cannot cancel appointment with status: {appointment.status}'
            }, status=400)
        
        slot = appointment.slot
        slot.is_booked = False
        slot.save()
        
        appointment.status = 'cancelled'
        appointment.save()
        
        return Response({
            'status': 'success',
            'message': f'Appointment with {appointment.patient.first_name} {appointment.patient.last_name} has been cancelled successfully.'
        })
        
    except Doctor.DoesNotExist:
        return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)
    except Appointment.DoesNotExist:
        return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)


######################################################
#doctor dashboard pa cancel missing ha 

# import uuid
# from datetime import datetime, timedelta, date
# from django.shortcuts import render, get_object_or_404
# from django.http import JsonResponse
# from django.db.models import Q
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from django.db import models  # ← ADD THIS LINE

# from .models import Doctor, Department, DoctorSchedule, TimeSlot, Appointment, Prescription
# from .serializers import (
#     DepartmentSerializer, DoctorSerializer, PatientAppointmentSerializer, 
#     PrescriptionDetailSerializer, DoctorAppointmentSerializer, DoctorScheduleUpdateSerializer ,DoctorScheduleSerializer
# )

# # ==================== RENDERING VIEWS ====================

# def doctor_profile_page_view(request, doc_id):
#     return render(request, 'appointment/doctor_profile.html', {'doc_id': doc_id})

# def doctor_list_page_view(request):
#     return render(request, 'appointment/doctors_list.html')

# def booking_page_view(request, doc_id):
#     if not request.user.is_authenticated:
#         return render(request, 'accounts/signin.html')
    
#     doctor = get_object_or_404(Doctor, id=doc_id)
#     raw_schedules = list(DoctorSchedule.objects.filter(doctor=doctor, is_available=True))
    
#     days_map = {
#         'monday': 0, 'tuesday': 1, 'wednesday': 2, 
#         'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
#     }
    
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


# # ==================== API VIEWS ====================

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


# # ==================== BOOKING HELPERS ====================

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
#             slot_start_24 = curr.time()
#             display_time = curr.strftime("%I:%M %p")
#             value_time = slot_start_24.strftime("%H:%M")
#             curr += timedelta(minutes=30)
            
#             if not TimeSlot.objects.filter(doctor_id=doctor_id, date=target_date, start_time=slot_start_24, is_booked=True).exists():
#                 slots.append({"display": display_time, "value": value_time})
        
#         return JsonResponse({
#             'slots': slots, 
#             'formatted_date': target_date.strftime("%d-%b-%Y"), 
#             'raw_date': target_date.strftime("%Y-%m-%d")
#         })
#     except DoctorSchedule.DoesNotExist:
#         return JsonResponse({'error': 'No schedule found'}, status=404)


# # ==================== MAIN BOOKING API ====================

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def book_appointment_api(request):
#     data = request.data
#     user = request.user

#     try:
#         doctor = Doctor.objects.get(id=data['doctor_id'])
        
#         if doctor.user.id == user.id:
#             return JsonResponse({'status': 'error', 'message': 'You cannot book an appointment with yourself.'}, status=400)

#         if not user.is_superuser and hasattr(user, 'role') and user.role == 'user':
#             user.role = 'patient'
#             user.save()

#         try:
#             paid_amount = float(data.get('paid_amount', 0))
#             if paid_amount < float(doctor.consultation_fee):
#                 return JsonResponse({'status': 'error', 'message': f'Insufficient fee. Minimum required is Rs. {doctor.consultation_fee}'}, status=400)
#         except ValueError:
#             return JsonResponse({'status': 'error', 'message': 'Invalid fee amount.'}, status=400)

#         booking_date = data['date']
#         start_time_str = data['start_time']
        
#         already_booked = Appointment.objects.filter(
#             patient=user, slot__date=booking_date, slot__start_time=start_time_str, status='confirmed'
#         ).exists()

#         if already_booked:
#             return JsonResponse({'status': 'error', 'message': 'You already have an appointment at this time.'}, status=400)

#         start_dt = datetime.strptime(start_time_str, "%H:%M")
#         end_time = (start_dt + timedelta(minutes=30)).time()

#         slot = TimeSlot.objects.create(
#             doctor=doctor, date=booking_date, start_time=start_time_str, end_time=end_time, is_booked=True
#         )
        
#         meeting_link = f"https://meet.jit.si/CareSync-{uuid.uuid4().hex[:10]}" if data['appointment_type'] == 'online' else ""

#         Appointment.objects.create(
#             patient=user, doctor=doctor, slot=slot,
#             appointment_type=data['appointment_type'],
#             medical_history=data.get('medical_history', ''),
#             status='confirmed', meeting_link=meeting_link
#         )
        
#         return JsonResponse({'status': 'success'})

#     except Doctor.DoesNotExist:
#         return JsonResponse({'message': 'Doctor not found'}, status=404)
#     except Exception as e:
#         return JsonResponse({'message': str(e)}, status=500)


# # ==================== PATIENT DASHBOARD VIEWS ====================

# def patient_dashboard_view(request):
#     if not request.user.is_authenticated:
#         return render(request, 'accounts/signin.html')
#     return render(request, 'appointment/patient_dashboard.html')

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_patient_appointments_api(request):
#     user = request.user
#     today = date.today()
    
#     fresh_appointments = Appointment.objects.filter(
#         patient=user, slot__date__gte=today
#     ).exclude(status='cancelled').select_related('doctor', 'doctor__user', 'doctor__department', 'slot').order_by('slot__date', 'slot__start_time')
    
#     cancelled_appointments = Appointment.objects.filter(
#         patient=user, status='cancelled'
#     ).select_related('doctor', 'doctor__user', 'doctor__department', 'slot').order_by('-slot__date')
    
#     return Response({
#         'fresh_appointments': PatientAppointmentSerializer(fresh_appointments, many=True).data,
#         'cancelled_appointments': PatientAppointmentSerializer(cancelled_appointments, many=True).data
#     })

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def cancel_appointment_api(request, appointment_id):
#     user = request.user
#     today = date.today()
    
#     try:
#         appointment = Appointment.objects.get(id=appointment_id, patient=user)
        
#         if appointment.status == 'cancelled':
#             return Response({'status': 'error', 'message': 'Already cancelled.'}, status=400)
        
#         if appointment.slot.date < today:
#             return Response({'status': 'error', 'message': 'Cannot cancel past appointments.'}, status=400)
        
#         appointment.slot.is_booked = False
#         appointment.slot.save()
#         appointment.status = 'cancelled'
#         appointment.save()
        
#         return Response({'status': 'success', 'message': 'Appointment cancelled successfully.'})
        
#     except Appointment.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_appointment_slip_api(request, appointment_id):
#     try:
#         appointment = Appointment.objects.get(id=appointment_id, patient=request.user)
#         return Response(PatientAppointmentSerializer(appointment).data)
#     except Appointment.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_prescription_api(request, appointment_id):
#     try:
#         appointment = Appointment.objects.get(id=appointment_id, patient=request.user)
        
#         if appointment.appointment_type != 'online':
#             return Response({'status': 'error', 'message': 'Prescription only for online consultations.'}, status=400)
        
#         prescription = Prescription.objects.get(appointment=appointment)
#         return Response(PrescriptionDetailSerializer(prescription).data)
#     except Appointment.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)
#     except Prescription.DoesNotExist:
#         return Response({'status': 'error', 'message': 'No prescription added yet.'}, status=404)


# # ==================== DOCTOR DASHBOARD VIEWS ====================

# def doctor_dashboard_view(request):
#     """Doctor Dashboard Page"""
#     if not request.user.is_authenticated:
#         return render(request, 'accounts/signin.html')
    
#     # Check if user is a doctor
#     try:
#         doctor = Doctor.objects.get(user=request.user)
#     except Doctor.DoesNotExist:
#         return render(request, 'error.html', {'message': 'You are not registered as a doctor.'})
    
#     return render(request, 'appointment/doctor_dashboard.html', {'doctor': doctor})


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_doctor_appointments_api(request):
#     """Get doctor's appointments"""
#     try:
#         doctor = Doctor.objects.get(user=request.user)
#     except Doctor.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)
    
#     today = date.today()
    
#     # Fresh appointments (today and future, not cancelled)
#     fresh_appointments = Appointment.objects.filter(
#         doctor=doctor, slot__date__gte=today
#     ).exclude(status='cancelled').select_related('patient', 'slot').order_by('slot__date', 'slot__start_time')
    
#     # Cancelled appointments
#     cancelled_appointments = Appointment.objects.filter(
#         doctor=doctor, status='cancelled'
#     ).select_related('patient', 'slot').order_by('-slot__date')
    
#     return Response({
#         'fresh_appointments': DoctorAppointmentSerializer(fresh_appointments, many=True).data,
#         'cancelled_appointments': DoctorAppointmentSerializer(cancelled_appointments, many=True).data
#     })


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def add_prescription_api(request, appointment_id):
#     """Add prescription for online appointment"""
#     try:
#         doctor = Doctor.objects.get(user=request.user)
#         appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)
        
#         # Check if appointment is online
#         if appointment.appointment_type != 'online':
#             return Response({'status': 'error', 'message': 'Prescriptions can only be added for online appointments.'}, status=400)
        
#         # Check if prescription already exists
#         if Prescription.objects.filter(appointment=appointment).exists():
#             return Response({'status': 'error', 'message': 'Prescription already added for this appointment.'}, status=400)
        
#         notes = request.data.get('notes', '').strip()
#         if not notes:
#             return Response({'status': 'error', 'message': 'Prescription notes are required.'}, status=400)
        
#         # Create prescription
#         prescription = Prescription.objects.create(
#             appointment=appointment,
#             doctor=doctor,
#             patient=appointment.patient,
#             notes=notes
#         )
        
#         # Update appointment status to completed if needed
#         # appointment.status = 'completed'
#         # appointment.save()
        
#         return Response({
#             'status': 'success',
#             'message': 'Prescription added successfully.',
#             'prescription': PrescriptionDetailSerializer(prescription).data
#         })
        
#     except Doctor.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)
#     except Appointment.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)
#     except Exception as e:
#         return Response({'status': 'error', 'message': str(e)}, status=500)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_doctor_schedules_api(request):
#     """Get doctor's current schedules"""
#     try:
#         doctor = Doctor.objects.get(user=request.user)
#         schedules = DoctorSchedule.objects.filter(doctor=doctor).order_by(
#             models.Case(
#                 models.When(day_of_week='monday', then=0),
#                 models.When(day_of_week='tuesday', then=1),
#                 models.When(day_of_week='wednesday', then=2),
#                 models.When(day_of_week='thursday', then=3),
#                 models.When(day_of_week='friday', then=4),
#                 models.When(day_of_week='saturday', then=5),
#                 models.When(day_of_week='sunday', then=6),
#                 default=7,
#             )
#         )
#         return Response(DoctorScheduleSerializer(schedules, many=True).data)
#     except Doctor.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def update_doctor_schedule_api(request):
#     """Update doctor's schedule - handles cancellations if schedule changes"""
#     try:
#         doctor = Doctor.objects.get(user=request.user)
#         schedule_data = request.data.get('schedules', [])
        
#         # Track which days are being updated
#         updated_days = []
        
#         for item in schedule_data:
#             day = item.get('day_of_week')
#             start_time = item.get('start_time')
#             end_time = item.get('end_time')
#             is_available = item.get('is_available', True)
            
#             if not day:
#                 continue
            
#             updated_days.append(day)
            
#             # Get or create schedule
#             schedule, created = DoctorSchedule.objects.get_or_create(
#                 doctor=doctor,
#                 day_of_week=day,
#                 defaults={
#                     'start_time': start_time,
#                     'end_time': end_time,
#                     'is_available': is_available
#                 }
#             )
            
#             if not created:
#                 # Check if schedule is being removed or changed
#                 old_start = schedule.start_time
#                 old_end = schedule.end_time
#                 old_available = schedule.is_available
                
#                 schedule.start_time = start_time
#                 schedule.end_time = end_time
#                 schedule.is_available = is_available
#                 schedule.save()
                
#                 # If schedule is being disabled or times changed, cancel affected appointments
#                 if not is_available or old_start != start_time or old_end != end_time:
#                     cancel_affected_appointments(doctor, day, old_start, old_end, start_time, end_time, is_available)
        
#         return Response({'status': 'success', 'message': 'Schedule updated successfully.'})
        
#     except Doctor.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)
#     except Exception as e:
#         return Response({'status': 'error', 'message': str(e)}, status=500)


# def cancel_affected_appointments(doctor, day_of_week, old_start, old_end, new_start, new_end, is_available):
#     """Cancel appointments that are no longer within working hours"""
#     from datetime import datetime, timedelta
    
#     # Get all future dates for this day of week
#     days_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
#     target_weekday = days_map.get(day_of_week.lower())
    
#     if target_weekday is None:
#         return
    
#     today = date.today()
    
#     # Find next occurrence of this day
#     current_date = today
#     while current_date.weekday() != target_weekday:
#         current_date += timedelta(days=1)
    
#     # Cancel appointments for next 90 days
#     for i in range(90):
#         appointment_date = current_date + timedelta(days=i*7)
        
#         # If doctor is not available on this day, cancel all appointments
#         if not is_available:
#             appointments = Appointment.objects.filter(
#                 doctor=doctor,
#                 slot__date=appointment_date,
#                 status='confirmed'
#             )
#         else:
#             # Cancel appointments that fall outside new working hours
#             appointments = Appointment.objects.filter(
#                 doctor=doctor,
#                 slot__date=appointment_date,
#                 slot__start_time__lt=new_start,
#                 status='confirmed'
#             ) | Appointment.objects.filter(
#                 doctor=doctor,
#                 slot__date=appointment_date,
#                 slot__end_time__gt=new_end,
#                 status='confirmed'
#             )
        
#         for appointment in appointments:
#             # Free up the slot
#             slot = appointment.slot
#             slot.is_booked = False
#             slot.save()
            
#             # Cancel appointment
#             appointment.status = 'cancelled'
#             appointment.save()


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_doctor_appointment_detail_api(request, appointment_id):
#     """Get single appointment detail for prescription"""
#     try:
#         doctor = Doctor.objects.get(user=request.user)
#         appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)
#         return Response(DoctorAppointmentSerializer(appointment).data)
#     except Doctor.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)
#     except Appointment.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_doctor_prescription_api(request, appointment_id):
#     """Get prescription for an appointment (for doctor view)"""
#     try:
#         doctor = Doctor.objects.get(user=request.user)
#         appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)
        
#         try:
#             prescription = Prescription.objects.get(appointment=appointment)
#             serializer = PrescriptionDetailSerializer(prescription)
#             return Response(serializer.data)
#         except Prescription.DoesNotExist:
#             return Response({
#                 'status': 'error',
#                 'message': 'No prescription added yet for this appointment.'
#             }, status=404)
        
#     except Doctor.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)
#     except Appointment.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)


# # ==================== DOCTOR CANCEL APPOINTMENT API ====================

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def doctor_cancel_appointment_api(request, appointment_id):
#     """Doctor cancels an appointment"""
#     try:
#         doctor = Doctor.objects.get(user=request.user)
#         appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)
        
#         if appointment.status == 'cancelled':
#             return Response({
#                 'status': 'error',
#                 'message': 'This appointment is already cancelled.'
#             }, status=400)
        
#         if appointment.status != 'confirmed':
#             return Response({
#                 'status': 'error',
#                 'message': f'Cannot cancel appointment with status: {appointment.status}'
#             }, status=400)
        
#         slot = appointment.slot
#         slot.is_booked = False
#         slot.save()
        
#         appointment.status = 'cancelled'
#         appointment.save()
        
#         return Response({
#             'status': 'success',
#             'message': f'Appointment with {appointment.patient.first_name} {appointment.patient.last_name} has been cancelled successfully.'
#         })
        
#     except Doctor.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Doctor not found.'}, status=404)
#     except Appointment.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Appointment not found.'}, status=404)
#     except Exception as e:
#         return Response({'status': 'error', 'message': str(e)}, status=500)



#patient dashaboard wala
# import uuid
# from datetime import datetime, timedelta, date
# from django.shortcuts import render, get_object_or_404
# from django.http import JsonResponse
# from django.db.models import Q
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated

# from .models import Doctor, Department, DoctorSchedule, TimeSlot, Appointment, Prescription
# from .serializers import DepartmentSerializer, DoctorSerializer, PatientAppointmentSerializer, PrescriptionDetailSerializer

# # --- Rendering Views (Pages) ---

# def doctor_profile_page_view(request, doc_id):
#     """Doctor ki profile page dikhane ke liye"""
#     return render(request, 'appointment/doctor_profile.html', {'doc_id': doc_id})

# def doctor_list_page_view(request):
#     """Saray doctors ki list wala page"""
#     return render(request, 'appointment/doctors_list.html')

# def booking_page_view(request, doc_id):
#     """Booking form jahan user data fill karega"""
#     if not request.user.is_authenticated:
#         return render(request, 'login.html') 

#     doctor = get_object_or_404(Doctor, id=doc_id)
#     raw_schedules = list(DoctorSchedule.objects.filter(doctor=doctor, is_available=True))
    
#     days_map = {
#         'monday': 0, 'tuesday': 1, 'wednesday': 2, 
#         'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
#     }
    
#     # Schedule kal se dikhana shuru karein
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
#     """Agli aane wali tareekh calculate karne ke liye"""
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
#     """Slots ko AM/PM format mein frontend bhejne ke liye lekin value 24h rakhi hai"""
#     doctor_id = request.GET.get('doctor_id')
#     day = request.GET.get('day')
#     try:
#         schedule = DoctorSchedule.objects.get(doctor_id=doctor_id, day_of_week=day, is_available=True)
#         target_date = get_next_date_of_day(day)
#         slots = []
#         curr = datetime.combine(target_date, schedule.start_time)
#         end = datetime.combine(target_date, schedule.end_time)
        
#         while curr < end:
#             slot_start_24 = curr.time()
#             # Display format (AM/PM) for User
#             display_time = curr.strftime("%I:%M %p")
#             # Raw format (24h) for Backend
#             value_time = slot_start_24.strftime("%H:%M")
            
#             curr += timedelta(minutes=30)
            
#             if not TimeSlot.objects.filter(doctor_id=doctor_id, date=target_date, start_time=slot_start_24, is_booked=True).exists():
#                 slots.append({
#                     "display": display_time,
#                     "value": value_time
#                 })
        
#         return JsonResponse({
#             'slots': slots, 
#             'formatted_date': target_date.strftime("%d-%b-%Y"), 
#             'raw_date': target_date.strftime("%Y-%m-%d")
#         })
#     except DoctorSchedule.DoesNotExist:
#         return JsonResponse({'error': 'No schedule found'}, status=404)

# # --- MAIN BOOKING API ---

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def book_appointment_api(request):
#     data = request.data
#     user = request.user

#     try:
#         doctor = Doctor.objects.get(id=data['doctor_id'])
        
#         # 1. Self-Booking Check
#         if doctor.user.id == user.id:
#             return JsonResponse({
#                 'status': 'error',
#                 'message': 'You cannot book an appointment with yourself.'
#             }, status=400)

#         # 2. Staff & Superuser Protection Logic
#         # Role sirf tab badle ga agar user Superuser na ho aur uska current role 'user' ho
#         if not user.is_superuser and hasattr(user, 'role') and user.role == 'user':
#             user.role = 'patient'
#             user.save()

#         # 3. Fee Validation (Double check on backend)
#         try:
#             paid_amount = float(data.get('paid_amount', 0))
#             if paid_amount < float(doctor.consultation_fee):
#                 return JsonResponse({
#                     'status': 'error',
#                     'message': f'Insufficient fee. Minimum required is Rs. {doctor.consultation_fee}'
#                 }, status=400)
#         except ValueError:
#             return JsonResponse({'status': 'error', 'message': 'Invalid fee amount.'}, status=400)

#         booking_date = data['date']
#         start_time_str = data['start_time'] # Ye already 24h format mein aayega
        
#         # 4. Double Booking Check
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

#         # 5. Save Data
#         start_dt = datetime.strptime(start_time_str, "%H:%M")
#         end_time = (start_dt + timedelta(minutes=30)).time()

#         slot = TimeSlot.objects.create(
#             doctor=doctor, 
#             date=booking_date, 
#             start_time=start_time_str, 
#             end_time=end_time, 
#             is_booked=True
#         )
        
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


# # ==================== PATIENT DASHBOARD VIEWS ====================

# def patient_dashboard_view(request):
#     """Patient Dashboard Page"""
#     if not request.user.is_authenticated:
#         return render(request, 'accounts/signin.html')
    
#     return render(request, 'appointment/patient_dashboard.html')


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_patient_appointments_api(request):
#     """Get patient's appointments (fresh: current date + future)"""
#     user = request.user
#     today = date.today()
    
#     # Get fresh appointments (today and future, not cancelled)
#     fresh_appointments = Appointment.objects.filter(
#         patient=user,
#         slot__date__gte=today
#     ).exclude(
#         status='cancelled'
#     ).select_related('doctor', 'doctor__user', 'doctor__department', 'slot').order_by('slot__date', 'slot__start_time')
    
#     # Get cancelled appointments history
#     cancelled_appointments = Appointment.objects.filter(
#         patient=user,
#         status='cancelled'
#     ).select_related('doctor', 'doctor__user', 'doctor__department', 'slot').order_by('-slot__date')
    
#     fresh_serializer = PatientAppointmentSerializer(fresh_appointments, many=True)
#     cancelled_serializer = PatientAppointmentSerializer(cancelled_appointments, many=True)
    
#     return Response({
#         'fresh_appointments': fresh_serializer.data,
#         'cancelled_appointments': cancelled_serializer.data
#     })


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def cancel_appointment_api(request, appointment_id):
#     """Cancel an appointment (only allowed on or before appointment date  appointment date)"""
#     user = request.user
#     today = date.today()
    
#     try:
#         appointment = Appointment.objects.get(id=appointment_id, patient=user)
        
#         if appointment.status == 'cancelled':
#             return Response({
#                 'status': 'error',
#                 'message': 'This appointment is already cancelled.'
#             }, status=400)
        
#         appointment_date = appointment.slot.date
        
#         if appointment_date < today:
#             return Response({
#                 'status': 'error',
#                 'message': 'You cannot cancel an appointment  after the appointment date.'
#             }, status=400)
        
#         # Free up the time slot
#         slot = appointment.slot
#         slot.is_booked = False
#         slot.save()
        
#         appointment.status = 'cancelled'
#         appointment.save()
        
#         return Response({
#             'status': 'success',
#             'message': 'Appointment cancelled successfully.'
#         })
        
#     except Appointment.DoesNotExist:
#         return Response({
#             'status': 'error',
#             'message': 'Appointment not found.'
#         }, status=404)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_appointment_slip_api(request, appointment_id):
#     """Get appointment slip details"""
#     user = request.user
    
#     try:
#         appointment = Appointment.objects.get(id=appointment_id, patient=user)
#         serializer = PatientAppointmentSerializer(appointment)
#         return Response(serializer.data)
#     except Appointment.DoesNotExist:
#         return Response({
#             'status': 'error',
#             'message': 'Appointment not found.'
#         }, status=404)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_prescription_api(request, appointment_id):
#     """Get prescription for an appointment (only for online appointments)"""
#     user = request.user
    
#     try:
#         appointment = Appointment.objects.get(id=appointment_id, patient=user)
        
#         if appointment.appointment_type != 'online':
#             return Response({
#                 'status': 'error',
#                 'message': 'Prescription is only available for online consultations.'
#             }, status=400)
        
#         try:
#             prescription = Prescription.objects.get(appointment=appointment)
#             serializer = PrescriptionDetailSerializer(prescription)
#             return Response(serializer.data)
#         except Prescription.DoesNotExist:
#             return Response({
#                 'status': 'error',
#                 'message': 'No prescription added yet by the doctor.'
#             }, status=404)
        
#     except Appointment.DoesNotExist:
#         return Response({
#             'status': 'error',
#             'message': 'Appointment not found.'
#         }, status=404)



#################################################################
#important without dashboards code 
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
#     """Doctor ki profile page dikhane ke liye"""
#     return render(request, 'appointment/doctor_profile.html', {'doc_id': doc_id})

# def doctor_list_page_view(request):
#     """Saray doctors ki list wala page"""
#     return render(request, 'appointment/doctors_list.html')

# def booking_page_view(request, doc_id):
#     """Booking form jahan user data fill karega"""
#     if not request.user.is_authenticated:
#         return render(request, 'login.html') 

#     doctor = get_object_or_404(Doctor, id=doc_id)
#     raw_schedules = list(DoctorSchedule.objects.filter(doctor=doctor, is_available=True))
    
#     days_map = {
#         'monday': 0, 'tuesday': 1, 'wednesday': 2, 
#         'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
#     }
    
#     # Schedule kal se dikhana shuru karein
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
#     """Agli aane wali tareekh calculate karne ke liye"""
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
#     """Slots ko AM/PM format mein frontend bhejne ke liye lekin value 24h rakhi hai"""
#     doctor_id = request.GET.get('doctor_id')
#     day = request.GET.get('day')
#     try:
#         schedule = DoctorSchedule.objects.get(doctor_id=doctor_id, day_of_week=day, is_available=True)
#         target_date = get_next_date_of_day(day)
#         slots = []
#         curr = datetime.combine(target_date, schedule.start_time)
#         end = datetime.combine(target_date, schedule.end_time)
        
#         while curr < end:
#             slot_start_24 = curr.time()
#             # Display format (AM/PM) for User
#             display_time = curr.strftime("%I:%M %p")
#             # Raw format (24h) for Backend
#             value_time = slot_start_24.strftime("%H:%M")
            
#             curr += timedelta(minutes=30)
            
#             if not TimeSlot.objects.filter(doctor_id=doctor_id, date=target_date, start_time=slot_start_24, is_booked=True).exists():
#                 slots.append({
#                     "display": display_time,
#                     "value": value_time
#                 })
        
#         return JsonResponse({
#             'slots': slots, 
#             'formatted_date': target_date.strftime("%d-%b-%Y"), 
#             'raw_date': target_date.strftime("%Y-%m-%d")
#         })
#     except DoctorSchedule.DoesNotExist:
#         return JsonResponse({'error': 'No schedule found'}, status=404)

# # --- MAIN BOOKING API ---

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def book_appointment_api(request):
#     data = request.data
#     user = request.user

#     try:
#         doctor = Doctor.objects.get(id=data['doctor_id'])
        
#         # 1. Self-Booking Check
#         if doctor.user.id == user.id:
#             return JsonResponse({
#                 'status': 'error',
#                 'message': 'You cannot book an appointment with yourself.'
#             }, status=400)

#         # 2. Staff & Superuser Protection Logic
#         # Role sirf tab badle ga agar user Superuser na ho aur uska current role 'user' ho
#         if not user.is_superuser and user.role == 'user':
#             user.role = 'patient'
#             user.save()

#         # 3. Fee Validation (Double check on backend)
#         try:
#             paid_amount = float(data.get('paid_amount', 0))
#             if paid_amount < float(doctor.consultation_fee):
#                 return JsonResponse({
#                     'status': 'error',
#                     'message': f'Insufficient fee. Minimum required is Rs. {doctor.consultation_fee}'
#                 }, status=400)
#         except ValueError:
#             return JsonResponse({'status': 'error', 'message': 'Invalid fee amount.'}, status=400)

#         booking_date = data['date']
#         start_time_str = data['start_time'] # Ye already 24h format mein aayega
        
#         # 4. Double Booking Check
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

#         # 5. Save Data
#         start_dt = datetime.strptime(start_time_str, "%H:%M")
#         end_time = (start_dt + timedelta(minutes=30)).time()

#         slot = TimeSlot.objects.create(
#             doctor=doctor, 
#             date=booking_date, 
#             start_time=start_time_str, 
#             end_time=end_time, 
#             is_booked=True
#         )
        
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