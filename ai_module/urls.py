from django.urls import path
from . import views

urlpatterns = [
    path("DietForm/", views.food_preferences_view, name="food_preferences"),
    path("result/", views.diet_result_view, name="diet_result"),
    path('diabetes-check/', views.diabetes_predict_view, name='diabetes_check'),
    # Stats Page: /ai/my-stats/
    path('my-stats/', views.health_stats_view, name='health_stats'),
    # API Endpoint: /ai/api/glucose-data/
    path('api/glucose-data/', views.GlucoseDataAPI.as_view(), name='glucose_api'),

]