
from django.shortcuts import render
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404 ,  redirect
from django.contrib.auth.decorators import login_required
from .models import LabTest, LabSchedule, LabBooking
from .serializers import LabTestSerializer, LabScheduleSerializer
from django.contrib import messages
from datetime import datetime

def lab_view(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'json' in request.GET:
        tests = LabTest.objects.all()
        
        # Serializer logic
        serializer = LabTestSerializer(tests, many=True)
        
        # serializer.data mein saara data (including id) maujood hota hai
        return JsonResponse({'tests': serializer.data})
    
    return render(request, 'lab/lab_reports.html')




# @login_required(login_url='signin')
# def book_appointment(request, test_id):
#     test = get_object_or_404(LabTest, id=test_id)
    
#     if request.method == 'POST':
#         selected_date_str = request.POST.get('test_date') # HTML se date aayi
#         patient_name = request.POST.get('name')
#         # 1. String date ko Python date object mein badlein
#         booking_date_obj = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        
#         # 2. Date se din ka naam nikalna (e.g., 'Monday')
#         # .lower() isliye taake database ke 'monday' se match ho jaye
#         day_of_week = booking_date_obj.strftime('%A').lower()
        
#         # 3. Database (LabSchedule) mein check karein kya is din lab 'is_open=True' hai
#         is_available = LabSchedule.objects.filter(day_of_week=day_of_week, is_open=True).exists()
        
#         if is_available:
#             # 4. Agar lab khuli hai toh booking save karein
#             LabBooking.objects.create(
#                 user=request.user,
#                 name=patient_name,
#                 test=test,
#                 test_date=booking_date_obj,
#                 status='booked'
#             )
#             messages.success(request, f"Booking Confirmed! Your appointment for {test.name} is set for {selected_date_str}.")
#             return redirect('lab_reports') # Wapis main page par bhej dein
#         else:
#             # 5. Agar lab band hai toh error message dein
#             messages.error(request, f"Invalid Entry! The lab is closed on {day_of_week.capitalize()}. Please choose another date.")
#             return redirect(request.path) # Dobara isi form par bhej dein

#     # GET request par sirf form dikhao
#     context = {
#         'test': test,
#         'user': request.user,
#     }
#     return render(request, 'lab/booking_form.html', context)
@login_required(login_url='signin')
def book_appointment(request, test_id):
    test = get_object_or_404(LabTest, id=test_id)
    
    if request.method == 'POST':
        selected_date_str = request.POST.get('test_date')
        patient_name = request.POST.get('name')
        booking_date_obj = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        day_of_week = booking_date_obj.strftime('%A').lower()
        
        is_available = LabSchedule.objects.filter(day_of_week=day_of_week, is_open=True).exists()
        
        if is_available:
            # Create the booking
            booking = LabBooking.objects.create(
                user=request.user,
                name=patient_name,
                test=test,
                test_date=booking_date_obj,
                status='booked'
            )
            # Add a specific tag to trigger the modal
            messages.success(request, "Success", extra_tags='booking_success')
            
            # Instead of redirecting immediately, we render to show the modal
            return render(request, 'lab/booking_form.html', {
                'test': test,
                'user': request.user,
                'booking_data': booking  # Pass the object to fill the modal
            })
        else:
            messages.error(request, f"The lab is closed on {day_of_week.capitalize()}. Please choose another date.")
            return redirect(request.path)

    return render(request, 'lab/booking_form.html', {'test': test, 'user': request.user})