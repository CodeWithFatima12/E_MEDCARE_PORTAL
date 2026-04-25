from rest_framework import serializers
from .models import Medicine, MedicineCategory, Cart, CartItem, Order, OrderItem

class MedicineCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineCategory
        fields = ['id', 'name','description']

class MedicineSerializer(serializers.ModelSerializer):
    # This brings the category name directly into the medicine object
    
    category_name = serializers.ReadOnlyField(source='category.name')
    
    class Meta:
        model = Medicine
        fields = ['id', 'name', 'category', 'category_name', 'price', 'stock_quantity', 'description', 'image']


class CartItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.ReadOnlyField(source='medicine.name')
    medicine_price = serializers.ReadOnlyField(source='medicine.price')
    medicine_image = serializers.ImageField(source='medicine.image', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id',
            'medicine_id',
            'medicine_name',
            'medicine_price',
            'medicine_image',
            'quantity',
            'subtotal'
        ]

    def get_subtotal(self, obj):
        return obj.quantity * obj.medicine.price