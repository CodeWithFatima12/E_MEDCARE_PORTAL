from django.urls import path
from . import views

urlpatterns = [
    path("DietForm/", views.food_preferences_view, name="food_preferences"),
    path("result/", views.diet_result_view, name="diet_result"),
]