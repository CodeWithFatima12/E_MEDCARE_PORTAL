
# Create your views here.
from django.shortcuts import render, redirect
from .forms import FoodCategoryForm
from .gemini import generate_diet_plan


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
