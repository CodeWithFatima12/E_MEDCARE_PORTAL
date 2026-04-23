from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Add 'role' to the list display so you can see it in the table
    list_display = ('username', 'email', 'role', 'is_staff')
    
    # Add 'role' to the user editing page
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )