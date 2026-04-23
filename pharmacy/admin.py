from django.contrib import admin
from .models import MedicineCategory, Medicine, Cart, CartItem, Order, OrderItem

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock_quantity')
    list_editable = ('stock_quantity', 'price') # Allows quick updates from the list view
    list_filter = ('category',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'total_amount', 'status', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('order_number', 'total_amount') # Keep these read-only for security

admin.site.register(MedicineCategory)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(OrderItem)
# Register your models here.
