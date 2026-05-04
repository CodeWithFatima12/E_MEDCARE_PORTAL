
#missing name,age,gender  cover
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
from django.core.mail import send_mail
from django.conf import settings

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
    
    user = request.user
    restricted_roles = ['doctor', 'pharmacist', 'lab_technician']
    
    

    
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
    restricted_roles = ['doctor', 'pharmacist', 'lab_technician']
    
    if user.is_superuser or user.is_staff or (hasattr(user, 'role') and user.role in restricted_roles):
         return JsonResponse({
             'status': 'error', 
             'message': 'Access Denied: Admins/Staff members cannot book appointments. Please use a regular patient account.'
         }, status=403)

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
    
    # FIXED: Sirf Today + Future ki cancelled appointments
    cancelled_appointments = Appointment.objects.filter(
        patient=user, 
        status='cancelled',
        slot__date__gte=today  # ← YEH LINE ADD KARI
    ).select_related('doctor', 'doctor__user', 'doctor__department', 'slot').order_by('slot__date', 'slot__start_time')  # ← order_by bhi change kiya
    
    return Response({
        'fresh_appointments': PatientAppointmentSerializer(fresh_appointments, many=True).data,
        'cancelled_appointments': PatientAppointmentSerializer(cancelled_appointments, many=True).data
    })

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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_appointment_api(request, appointment_id):
    user = request.user
    
    try:
        # Fetch the appointment and ensure it belongs to the logged-in user
        appointment = Appointment.objects.get(id=appointment_id, patient=user)
        
        # 1. Check if already cancelled
        if appointment.status == 'cancelled':
            return Response({
                'status': 'error', 
                'message': 'This appointment has already been cancelled.'
            }, status=400)

        # 2. Combine date and time for comparison
        # Ensure your models use date and time objects correctly
        apt_datetime = datetime.combine(appointment.slot.date, appointment.slot.start_time)
        now = datetime.now()
        
        # 3. Prevent cancelling past appointments
        if apt_datetime < now:
            return Response({
                'status': 'error', 
                'message': 'Cannot cancel past appointments.'
            }, status=400)

        # 4. The 2-Hour Restriction Logic
        time_diff = apt_datetime - now
        if time_diff < timedelta(hours=2):
            return Response({
                'status': 'error', 
                'message': 'Cancellation is only allowed up to 2 hours before the appointment start time.'
            }, status=400)
        
        # 5. Execute Cancellation
        # Free up the time slot so others can book it
        appointment.slot.is_booked = False
        appointment.slot.save()
        
        # Update appointment status
        appointment.status = 'cancelled'
        appointment.save()
        
        return Response({
            'status': 'success', 
            'message': 'Your appointment has been cancelled successfully.'
        })
        
    except Appointment.DoesNotExist:
        return Response({
            'status': 'error', 
            'message': 'Appointment record not found.'
        }, status=404)
    except Exception as e:
        return Response({
            'status': 'error', 
            'message': f'An unexpected error occurred: {str(e)}'
        }, status=500)

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
    
    #  FIXED: Sirf Today + Future ki cancelled appointments
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

# def cancel_affected_appointments(doctor, day_of_week, old_start, old_end, new_start, new_end, is_available):
#     """Cancel appointments that are no longer within working hours"""
#     days_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
#     target_weekday = days_map.get(day_of_week.lower())
    
#     if target_weekday is None:
#         return
    
#     today = date.today()
#     current_date = today
#     while current_date.weekday() != target_weekday:
#         current_date += timedelta(days=1)
    
#     for i in range(90):
#         appointment_date = current_date + timedelta(days=i*7)
        
#         if not is_available:
#             appointments = Appointment.objects.filter(
#                 doctor=doctor, slot__date=appointment_date, status='confirmed'
#             )
#         else:
#             appointments = Appointment.objects.filter(
#                 doctor=doctor, slot__date=appointment_date, slot__start_time__lt=new_start, status='confirmed'
#             ) | Appointment.objects.filter(
#                 doctor=doctor, slot__date=appointment_date, slot__end_time__gt=new_end, status='confirmed'
#             )
        
#         for appointment in appointments:
#             slot = appointment.slot
#             slot.is_booked = False
#             slot.save()
#             appointment.status = 'cancelled'
#             appointment.save()


def cancel_affected_appointments(doctor, day_of_week, old_start, old_end, new_start, new_end, is_available):
    """Cancel appointments that are no longer within working hours and notify patients"""
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
            # 1. Store patient info before changing status
            # 1. Sahi Patient Name ki logic (Serializer wali)
            if appointment.patient_name:
                patient_name = appointment.patient_name.title()
            else:
                patient_name = f"{appointment.patient.first_name} {appointment.patient.last_name}".title()
            patient_email = appointment.patient.email
            # patient_name = appointment.patient.first_name
            doc_name = f"Dr. {doctor.user.last_name}"
            apt_date = appointment.slot.date.strftime('%d-%b-%Y')
            apt_time = appointment.slot.start_time.strftime('%I:%M %p')

            # 2. Perform database updates
            slot = appointment.slot
            slot.is_booked = False
            slot.save()
            appointment.status = 'cancelled'
            appointment.save()

            # 3. Send Email Notification
            subject = "Appointment Cancellation - Schedule Change"
            message = (
                f"Dear {patient_name},\n\n"
                f"We regret to inform you that your appointment with {doc_name} "
                f"on {apt_date} at {apt_time} has been cancelled because the doctor's "
                f"working hours have changed.\n\n"
                f"Please log in to the E-Medcare portal to book a new available slot.\n\n"
                f"Best regards,\nCareSync Team"
            )

            try:
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [patient_email],
                    fail_silently=False,
                )
            except Exception as e:
                # If email is fake or fails, we log it to console but keep going
                print(f"!!! Notification failed for {patient_email}: {e} !!!")
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


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def doctor_cancel_appointment_api(request, appointment_id):
#     """Doctor cancels an appointment"""
#     try:
#         # 1. Verify the user is a registered doctor
#         doctor = Doctor.objects.get(user=request.user)
#         appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)
        
#         # 2. Check if already cancelled
#         if appointment.status == 'cancelled':
#             return Response({
#                 'status': 'error',
#                 'message': 'This appointment is already cancelled.'
#             }, status=400)
        
#         # 3. Check if appointment is already completed
#         if appointment.status == 'completed':
#             return Response({
#                 'status': 'error',
#                 'message': 'Cannot cancel an appointment that has already been completed.'
#             }, status=400)

#         # 4. Past Date Check
#         # Doctors should not be able to cancel appointments from previous days
#         if appointment.slot.date < date.today():
#             return Response({
#                 'status': 'error',
#                 'message': 'Cannot cancel past appointments.'
#             }, status=400)
        
#         # 5. Execute Cancellation 
#         # (No 2-hour restriction for doctors, they have full control)
#         slot = appointment.slot
#         slot.is_booked = False
#         slot.save()
        
#         appointment.status = 'cancelled'
#         appointment.save()
        
#         # Pro-Tip: You could trigger an Email/SMS notification here to inform the patient
        
#         return Response({
#             'status': 'success',
#             'message': f'Appointment with {appointment.patient.first_name} has been cancelled.'
#         })
        
#     except Doctor.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Doctor profile not found.'}, status=404)
#     except Appointment.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Appointment record not found.'}, status=404)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def doctor_cancel_appointment_api(request, appointment_id):
    try:
        # 1. Doctor aur Appointment identify karein
        doctor = Doctor.objects.get(user=request.user)
        appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)
        
        if appointment.status == 'cancelled':
            return Response({'status': 'error', 'message': 'Already cancelled.'}, status=400)
        
        # Patient details for email
        patient_email = appointment.patient.email
        # patient_name = f"{appointment.patient.first_name}"
        if appointment.patient_name:
            patient_name = appointment.patient_name.title()
        else:
            patient_name = f"{appointment.patient.first_name} {appointment.patient.last_name}".title()
        
        doc_name = f"Dr. {doctor.user.last_name}"

        # 2. Status Update (Database kaam pehle)
        appointment.slot.is_booked = False
        appointment.slot.save()
        appointment.status = 'cancelled'
        appointment.save()

        # 3. Email Logic with Error Handling
        subject = "Appointment Cancellation Notice"
        message = f"Hi {patient_name}, your appointment with {doc_name} has been cancelled."
        
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [patient_email],
                fail_silently=False, # Taake error console mein dikhayi de
            )
            email_log = "Email sent successfully."
        except Exception as e:
            # Agar email fake hai toh yahan error print hoga
            print(f"--- EMAIL ERROR: {e} ---")
            email_log = "Email failed, but appointment cancelled in system."

        return Response({
            'status': 'success', 
            'message': f'Appointment cancelled. Status: {email_log}'
        })

    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)