from django import forms

class FoodCategoryForm(forms.Form):
    # --- NEW: User Metrics ---
    age = forms.IntegerField(
        label="Age",
        min_value=10,
        max_value=120,
        required=True,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g., 25"})
    )
    
    height = forms.IntegerField(
    label="Height (in total inches)",
    min_value=20,
    max_value=120,
    required=True,
    widget=forms.NumberInput(attrs={
        "class": "form-control", 
        "placeholder": "e.g., 63 for 5'3\""
    }),
    help_text="Example: 5'3\" is 63 inches, 5'10\" is 70 inches."
)
    weight = forms.FloatField(
        label="Weight (in kg)",
        min_value=20,
        max_value=300,
        required=True,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g., 70"})
    )
    gender = forms.ChoiceField(
        choices=[('male', 'Male'), ('female', 'Female')],
        label="Gender",
        required=True,
        widget=forms.Select(attrs={"class": "form-select"})
    )


    GOAL_CHOICES = [
        ('lose', 'Lose Weight'),
        ('gain', 'Gain Weight'),
        ('maintain', 'Maintain Weight')
    ]
    goal = forms.ChoiceField(
        choices=GOAL_CHOICES,
        label="What is your goal?",
        required=True,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    duration = forms.IntegerField(
        label="Diet Plan Duration (Max 15 Days)",
        min_value=1,
        max_value=15,
        required=True,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g., 7"})
    )

    # --- Existing: Region Selection ---
    REGION_CHOICES = [
        ('global', 'Global/General'),
        ('south_asia', 'South Asian (Indian, Pakistani, etc.)'),
        ('middle_east', 'Middle Eastern'),
        ('mediterranean', 'Mediterranean'),
        ('east_asia', 'East Asian'),
        ('western', 'Western/American'),
    ]
    
    region = forms.ChoiceField(
        choices=REGION_CHOICES,
        label="Your Region (for local food options)",
        required=True,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    country = forms.CharField(
        label="Specific Country", 
        required=False, 
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Pakistan"})
    )

    # --- Existing: Disliked Categories ---
    vegetables = forms.CharField(label="Disliked Vegetables", required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., broccoli"}))
    fruits = forms.CharField(label="Disliked Fruits", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    dairy_products = forms.CharField(label="Disliked Dairy", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    meat_items = forms.CharField(label="Disliked Meats", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    dry_fruits = forms.CharField(label="Disliked Dry Fruits", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    lentils = forms.CharField(label="Disliked Lentils", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    seafood = forms.CharField(label="Disliked Seafood", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    flour_items = forms.CharField(label="Disliked Flour/Bread", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    sweets = forms.CharField(label="Disliked Sweets", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))

    def get_data_for_gemini(self):
        """
        Returns a dictionary containing the metrics, region, and the list of dislikes.
        """
        dislikes = []
        # Fields that should NOT be added to the 'dislikes' list
        non_dislike_fields = ['age', 'height', 'weight','gender', 'goal', 'duration', 'region', 'country']
        
        for field_name, value in self.cleaned_data.items():
            if field_name not in non_dislike_fields and value:
                items = [item.strip() for item in value.split(",") if item.strip()]
                dislikes.extend(items)
        
        return {
            "age": self.cleaned_data.get('age'),
            "height": self.cleaned_data.get('height'),
            "weight": self.cleaned_data.get('weight'),
            "gender": self.cleaned_data.get('gender'),
            "goal": self.cleaned_data.get('goal'),
            "duration": self.cleaned_data.get('duration'),
            "region": self.cleaned_data.get('region'),
            "country": self.cleaned_data.get('country'),
            "dislikes": dislikes
        }