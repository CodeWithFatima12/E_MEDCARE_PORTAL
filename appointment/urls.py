from django.urls import path
from .views import (
    DepartmentListView, 
    DoctorListView, 
    DoctorDetailAPIView, 
    doctor_list_page_view, 
    doctor_profile_page_view,
    # Naye functions yahan add kiye hain
    booking_page_view,
    get_available_slots_api,
    book_appointment_api
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
]


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