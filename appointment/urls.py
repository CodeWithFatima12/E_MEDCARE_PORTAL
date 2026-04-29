
from django.urls import path
from .views import (
    DepartmentListView, 
    DoctorListView, 
    DoctorDetailAPIView, 
    doctor_list_page_view, 
    doctor_profile_page_view,
    booking_page_view,
    get_available_slots_api,
    book_appointment_api,
    # Patient Dashboard Views
    patient_dashboard_view,
    get_patient_appointments_api,
    cancel_appointment_api,
    get_appointment_slip_api,
    get_prescription_api,
    # Doctor Dashboard Views
    doctor_dashboard_view,
    get_doctor_appointments_api,
    add_prescription_api,
    get_doctor_schedules_api,
    update_doctor_schedule_api,
    get_doctor_appointment_detail_api,
    get_doctor_prescription_api,
    doctor_cancel_appointment_api,
)

urlpatterns = [
    # Doctors List Page
    path('doctors/', doctor_list_page_view, name='doctors-list-page'),
    
    # API for Departments
    path('departments/', DepartmentListView.as_view(), name='dept-api'),
    
    # API for Doctors List
    path('doctors-api/', DoctorListView.as_view(), name='doctors-api'),

    # Profile Page
    path('profile/<int:doc_id>/', doctor_profile_page_view, name='doctor-profile-page'),
    
    # Doctor Detail API
    path('doctor-detail-api/<int:doc_id>/', DoctorDetailAPIView.as_view(), name='doctor-detail-api'),

    # --- Booking Logic Routes ---
    path('book/<int:doc_id>/', booking_page_view, name='booking-page'),
    path('get-slots/', get_available_slots_api, name='get-slots'),
    path('confirm-booking/', book_appointment_api, name='confirm-booking'),
    
    # --- Patient Dashboard Routes ---
    path('patient-dashboard/', patient_dashboard_view, name='patient-dashboard'),
    path('patient/appointments/', get_patient_appointments_api, name='patient-appointments-api'),
    path('patient/cancel-appointment/<int:appointment_id>/', cancel_appointment_api, name='cancel-appointment-api'),
    path('patient/appointment-slip/<int:appointment_id>/', get_appointment_slip_api, name='appointment-slip-api'),
    path('patient/prescription/<int:appointment_id>/', get_prescription_api, name='prescription-api'),
    
    # --- Doctor Dashboard Routes ---
    path('doctor-dashboard/', doctor_dashboard_view, name='doctor-dashboard'),
    path('doctor/appointments/', get_doctor_appointments_api, name='doctor-appointments-api'),
    path('doctor/appointment/<int:appointment_id>/', get_doctor_appointment_detail_api, name='doctor-appointment-detail-api'),
    path('doctor/add-prescription/<int:appointment_id>/', add_prescription_api, name='add-prescription-api'),
    path('doctor/prescription/<int:appointment_id>/', get_doctor_prescription_api, name='doctor-prescription-api'),
    path('doctor/schedules/', get_doctor_schedules_api, name='doctor-schedules-api'),
    path('doctor/update-schedule/', update_doctor_schedule_api, name='update-schedule-api'),
    path('doctor/cancel-appointment/<int:appointment_id>/', doctor_cancel_appointment_api, name='doctor-cancel-appointment-api'),
]
#missing cancel button for doctor 


# from django.urls import path
# from .views import (
#     DepartmentListView, 
#     DoctorListView, 
#     DoctorDetailAPIView, 
#     doctor_list_page_view, 
#     doctor_profile_page_view,
#     booking_page_view,
#     get_available_slots_api,
#     book_appointment_api,
#     # Patient Dashboard Views
#     patient_dashboard_view,
#     get_patient_appointments_api,
#     cancel_appointment_api,
#     get_appointment_slip_api,
#     get_prescription_api,
#     # Doctor Dashboard Views
#     doctor_dashboard_view,
#     get_doctor_appointments_api,
#     add_prescription_api,
#     get_doctor_schedules_api,
#     update_doctor_schedule_api,
#     get_doctor_appointment_detail_api,
#     get_doctor_prescription_api,
# )

# urlpatterns = [
#     # Doctors List Page
#     path('doctors/', doctor_list_page_view, name='doctors-list-page'),
    
#     # API for Departments
#     path('departments/', DepartmentListView.as_view(), name='dept-api'),
    
#     # API for Doctors List
#     path('doctors-api/', DoctorListView.as_view(), name='doctors-api'),

#     # Profile Page
#     path('profile/<int:doc_id>/', doctor_profile_page_view, name='doctor-profile-page'),
    
#     # Doctor Detail API
#     path('doctor-detail-api/<int:doc_id>/', DoctorDetailAPIView.as_view(), name='doctor-detail-api'),

#     # --- Booking Logic Routes ---
#     path('book/<int:doc_id>/', booking_page_view, name='booking-page'),
#     path('get-slots/', get_available_slots_api, name='get-slots'),
#     path('confirm-booking/', book_appointment_api, name='confirm-booking'),
    
#     # --- Patient Dashboard Routes ---
#     path('patient-dashboard/', patient_dashboard_view, name='patient-dashboard'),
#     path('patient/appointments/', get_patient_appointments_api, name='patient-appointments-api'),
#     path('patient/cancel-appointment/<int:appointment_id>/', cancel_appointment_api, name='cancel-appointment-api'),
#     path('patient/appointment-slip/<int:appointment_id>/', get_appointment_slip_api, name='appointment-slip-api'),
#     path('patient/prescription/<int:appointment_id>/', get_prescription_api, name='prescription-api'),
    
#     # --- Doctor Dashboard Routes ---
#     path('doctor-dashboard/', doctor_dashboard_view, name='doctor-dashboard'),
#     path('doctor/appointments/', get_doctor_appointments_api, name='doctor-appointments-api'),
#     path('doctor/appointment/<int:appointment_id>/', get_doctor_appointment_detail_api, name='doctor-appointment-detail-api'),
#     path('doctor/add-prescription/<int:appointment_id>/', add_prescription_api, name='add-prescription-api'),
#     path('doctor/prescription/<int:appointment_id>/', get_doctor_prescription_api, name='doctor-prescription-api'), 
#     path('doctor/schedules/', get_doctor_schedules_api, name='doctor-schedules-api'),
#     path('doctor/update-schedule/', update_doctor_schedule_api, name='update-schedule-api'),
    

    
# ]

#with patient dashbaord 

# from django.urls import path
# from .views import (
#     DepartmentListView, 
#     DoctorListView, 
#     DoctorDetailAPIView, 
#     doctor_list_page_view, 
#     doctor_profile_page_view,
#     booking_page_view,
#     get_available_slots_api,
#     book_appointment_api,
#     # Patient Dashboard Views
#     patient_dashboard_view,
#     get_patient_appointments_api,
#     cancel_appointment_api,
#     get_appointment_slip_api,
#     get_prescription_api,
# )

# urlpatterns = [
#     # Doctors List Page
#     path('doctors/', doctor_list_page_view, name='doctors-list-page'),
    
#     # API for Departments
#     path('departments/', DepartmentListView.as_view(), name='dept-api'),
    
#     # API for Doctors List
#     path('doctors-api/', DoctorListView.as_view(), name='doctors-api'),

#     # Profile Page
#     path('profile/<int:doc_id>/', doctor_profile_page_view, name='doctor-profile-page'),
    
#     # Doctor Detail API
#     path('doctor-detail-api/<int:doc_id>/', DoctorDetailAPIView.as_view(), name='doctor-detail-api'),

#     # --- Booking Logic Routes ---
#     path('book/<int:doc_id>/', booking_page_view, name='booking-page'),
#     path('get-slots/', get_available_slots_api, name='get-slots'),
#     path('confirm-booking/', book_appointment_api, name='confirm-booking'),
    
#     # --- Patient Dashboard Routes ---
#     path('patient-dashboard/', patient_dashboard_view, name='patient-dashboard'),
#     path('patient/appointments/', get_patient_appointments_api, name='patient-appointments-api'),
#     path('patient/cancel-appointment/<int:appointment_id>/', cancel_appointment_api, name='cancel-appointment-api'),
#     path('patient/appointment-slip/<int:appointment_id>/', get_appointment_slip_api, name='appointment-slip-api'),
#     path('patient/prescription/<int:appointment_id>/', get_prescription_api, name='prescription-api'),
# ]


#important without dashboard code 
# from django.urls import path
# from .views import (
#     DepartmentListView, 
#     DoctorListView, 
#     DoctorDetailAPIView, 
#     doctor_list_page_view, 
#     doctor_profile_page_view,
#     # Naye functions yahan add kiye hain
#     booking_page_view,
#     get_available_slots_api,
#     book_appointment_api
# )

# urlpatterns = [
#     # Doctors List Page
#     path('doctors/', doctor_list_page_view, name='doctors-list-page'),
    
#     # API for Departments
#     path('departments/', DepartmentListView.as_view(), name='dept-api'),
    
#     # API for Doctors List
#     path('doctors-api/', DoctorListView.as_view(), name='doctors-api'),

#     # Profile Page
#     path('profile/<int:doc_id>/', doctor_profile_page_view, name='doctor-profile-page'),
    
#     # Doctor Detail API
#     path('doctor-detail-api/<int:doc_id>/', DoctorDetailAPIView.as_view(), name='doctor-detail-api'),

#     # --- Booking Logic Routes ---
#     path('book/<int:doc_id>/', booking_page_view, name='booking-page'),
#     path('get-slots/', get_available_slots_api, name='get-slots'),
#     path('confirm-booking/', book_appointment_api, name='confirm-booking'),
# ]


################################################
# from django.urls import path
# # Yahan se humne direct functions/classes mangwa li hain
# from .views import (
#     DepartmentListView, 
#     DoctorListView, 
#     DoctorDetailAPIView, 
#     doctor_list_page_view, 
#     doctor_profile_page_view
# )

# urlpatterns = [
#     # Doctors List Page
#     path('doctors/', doctor_list_page_view, name='doctors-list-page'),
    
#     # API for Departments
#     path('departments/', DepartmentListView.as_view(), name='dept-api'),
    
#     # API for Doctors List
#     path('doctors-api/', DoctorListView.as_view(), name='doctors-api'),

#     # Profile Page (Yahan se views. hata diya gaya hai)
#     path('profile/<int:doc_id>/', doctor_profile_page_view, name='doctor-profile-page'),
    
#     # Doctor Detail API (Yahan se bhi views. hata diya gaya hai)
#     path('doctor-detail-api/<int:doc_id>/', DoctorDetailAPIView.as_view(), name='doctor-detail-api'),
# ]



############################################3









# from django.urls import path
# from .views import DepartmentListView , DoctorListView , DoctorDetailAPIView , doctor_list_page_view , doctor_profile_page_view   
    

# urlpatterns = [
#     # Full URL: /api/appointment/departments/\
#     path('doctors/', doctor_list_page_view, name='doctors-list-page'),
#     path('departments/', DepartmentListView.as_view(), name='dept-api'),
#     path('doctors-api/', DoctorListView.as_view(), name='doctors-api'),

#     # Jab user card par click karega to URL kuch aisa hoga: /api/appointment/profile/1/
#     path('profile/<int:doc_id>/', views.doctor_profile_page_view, name='doctor-profile-page'),
#     path('doctor-detail-api/<int:doc_id>/', views.DoctorDetailAPIView.as_view(), name='doctor-detail-api'),

# ]