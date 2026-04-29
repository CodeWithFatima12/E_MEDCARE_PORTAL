
# Create your views here.
from django.shortcuts import render, redirect
from .forms import FoodCategoryForm
from .gemini import generate_diet_plan
import joblib
import pandas as pd
import os
from django.shortcuts import render
from .form import DiabetesPredictionForm
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from .models import HealthMetric
from .serializers import HealthMetricSerializer

# View For Gemini Response
def food_preferences_view(request):

    if request.method == "POST":
        form = FoodCategoryForm(request.POST)

        if form.is_valid():

            user_data = form.get_data_for_gemini()

            result = generate_diet_plan(user_data)

            # Save result temporarily
            request.session["diet_result"] = result

            # Go to next page
            return redirect("diet_result")

    else:
        form = FoodCategoryForm()

    return render(request, "ai_module/DietForm.html", {"form": form})


def diet_result_view(request):

    result = request.session.get("diet_result")

    if not result:
        return redirect("food_preferences")

    status_message = result.get("status_info")
    diet_plan = result.get("plan")

    return render(request, "ai_module/DietPlanResult.html", {
        "status_message": status_message,
        "diet_plan": diet_plan
    })

# for diabetes prediction
# Load model and scaler once when server starts
MODEL_PATH = os.path.join(settings.BASE_DIR, 'saved_models', 'diabetes_model.sav')
SCALER_PATH = os.path.join(settings.BASE_DIR, 'saved_models', 'scaler.sav')

model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

def diabetes_predict_view(request):
    result = None
    form = DiabetesPredictionForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        
        # 1. Preprocessing (Exact match to Streamlit)
        g_val = 1 if data['gender'] == "Male" else 0
        ratio = data['glucose'] / (data['bmi'] + 1e-3)
        
        # 2. Features List (Exact same order as training)
        cols = ['gender', 'age', 'hypertension', 'heart_disease', 'smoking_history', 
                'bmi', 'HbA1c_level', 'blood_glucose_level', 'glucose_bmi_ratio']
        
        input_df = pd.DataFrame([[
            g_val, data['age'], int(data['hypertension']), int(data['heart_disease']),
            int(data['smoking_history']), data['bmi'], data['hba1c'], data['glucose'], ratio
        ]], columns=cols)

        # 3. Scaling & Prediction
        input_scaled = scaler.transform(input_df)
        prediction = model.predict(input_scaled)[0]
        prob = model.predict_proba(input_scaled)[0]

        # 4. Clinical Logic (Strict match to your Streamlit code)
        hba1c = data['hba1c']
        glucose = data['glucose']
        
        status = "HEALTHY"
        color = "success"
        message = "Patient values are within the healthy range."
        
        # LOGIC FIX: Matching the Streamlit nested if/else structure
        if prediction == 1:
            # Check for Prediabetes range even if model says 1
            if ((5.7 <= hba1c <= 6.4) or (100 <= glucose <= 125)) and (hba1c < 6.5) and (glucose < 126):
                status = "PREDIABETES"
                color = "warning"
                message = "Clinical Observation: Patient falls in the prediabetic range based on HbA1c and Blood Glucose levels. Early lifestyle intervention is recommended."
                confidence = prob[1] * 100 # Probability of being Diabetic

            else:
                status = "DIABETIC"
                color = "danger"
                message = "Clinical Observation: Patient meets the high-risk criteria based on clinical standards."
                confidence = prob[1] * 100 # Probability of being Diabetic
        
        else:
            # Check for Prediabetes range even if model says 0
            if (5.7 <= hba1c <= 6.4) or (100 <= glucose <= 125):
                status = "PREDIABETES"
                color = "warning"
                message = "Clinical Observation: Patient falls in the prediabetic range based on HbA1c and Blood Glucose levels. Early lifestyle intervention is recommended."
                confidence = prob[0] * 100 # Probability of being Healthy
            else:
                status = "HEALTHY"
                color = "success"
                message = "Clinical Observation: Patient values are within the healthy range."
                confidence = prob[0] * 100 # Probability of being Healthy

        if request.user.is_authenticated:
            HealthMetric.objects.create(
                user=request.user,
                glucose_level=data['glucose'],
                bmi=data['bmi'],
                hba1c=data['hba1c']
            )

        result = {
            'status': status,
            'color': color,
            'message': message,
            'confidence': round(confidence, 2),
            'name': data['name']
        }

    return render(request, 'ai_module/diabetes_form.html', {'form': form, 'result': result})


class GlucoseDataAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the filter from URL e.g., /api/glucose/?range=7
        days = int(request.query_params.get('range', 30)) 
        start_date = timezone.now() - timedelta(days=days)
        
        metrics = HealthMetric.objects.filter(
            user=request.user, 
            created_at__gte=start_date
        ).order_by('created_at')  # <--- Added this to ensure the graph flows left-to-right
        
        serializer = HealthMetricSerializer(metrics, many=True)
        return Response(serializer.data)
    
from django.contrib.auth.decorators import login_required

# Add this function to your views.py
@login_required
def health_stats_view(request):
    """
    Renders the page that contains the Chart.js graph.
    The actual data is fetched by the GlucoseDataAPI via JavaScript.
    """
    return render(request, 'ai_module/graph.html')