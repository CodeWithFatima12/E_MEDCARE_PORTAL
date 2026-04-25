from django.shortcuts import render
from django.db import transaction
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Medicine, Cart, CartItem, Order, OrderItem, MedicineCategory
from .serializers import MedicineSerializer, CartItemSerializer,MedicineCategorySerializer
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.cache import never_cache
import uuid



class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MedicineCategory.objects.all()
    serializer_class = MedicineCategorySerializer
    pagination_class = None

class MedicineViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    # 'category__name' allows you to filter by the string name (like 'Vitamins')
    filterset_fields = ['category__name'] 
    search_fields = ['category__name']

class CartViewSet(viewsets.ViewSet):

    permission_classes = [IsAuthenticated]

    # GET CART
    def list(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        items = CartItem.objects.filter(cart=cart)
        serializer = CartItemSerializer(items, many=True)

        total = sum(item.quantity * item.medicine.price for item in items)

        return Response({
            "items": serializer.data,
            "total": total,
            "count": items.count()
        })


    # ADD TO CART
    @action(detail=False, methods=['post'])
    def add(self, request):
        user = request.user
        medicine_id = request.data.get('medicine_id')

        cart, created = Cart.objects.get_or_create(user=user)
        medicine = get_object_or_404(Medicine, id=medicine_id)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            medicine=medicine,
            defaults={'quantity': 1}
        )

        if not created:
            cart_item.quantity += 1
            cart_item.save()

        return Response({"message": "Added to cart"})


    # INCREASE / DECREASE
    @action(detail=False, methods=['post'])
    def update_qty(self, request):
        item_id = request.data.get('item_id')
        action_type = request.data.get('action')

        item = get_object_or_404(CartItem, id=item_id)

        if action_type == "increase":
            item.quantity += 1
        elif action_type == "decrease":
            if item.quantity > 1:
                item.quantity -= 1
            else:
                item.delete()
                return Response({"message": "Item removed"})

        item.save()
        return Response({"message": "Updated"})


    # REMOVE ITEM
    @action(detail=False, methods=['post'])
    def remove(self, request):
        item_id = request.data.get('item_id')
        item = get_object_or_404(CartItem, id=item_id)
        item.delete()
        return Response({"message": "Removed"})




@api_view(['GET'])
@permission_classes([IsAuthenticated])
@never_cache 
def cart_count(request):
    total = CartItem.objects.filter(
        cart__user=request.user
    ).aggregate(total=Sum('quantity'))['total'] or 0

    return Response({"count": total})

def checkout_view(request):
    user = request.user # یہ لائن لاگ ان یوزر کا پورا ابجیکٹ لے آئے گی
    cart = Cart.objects.get(user=user)
    cart_items = CartItem.objects.filter(cart=cart)
    total = sum(item.medicine.price * item.quantity for item in cart_items)

    context = {
        'user': user,  # یوزر کا ڈیٹا یہاں سے جائے گا
        'cart_items': cart_items,
        'total': total
    }
    return render(request, 'pharmacy/checkout.html', context)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def place_order(request):
    user = request.user
    # ڈیٹا حاصل کرنا (request.POST یا request.data دونوں کے لیے محفوظ طریقہ)
    address = request.data.get('address') or request.POST.get('address')
    
    if not address:
        return Response({"error": "براہ کرم ایڈریس درج کریں"}, status=400)

    try:
        with transaction.atomic():
            # 1. یوزر کا کارٹ حاصل کریں
            cart = get_object_or_404(Cart, user=user)
            cart_items = CartItem.objects.filter(cart=cart)

            if not cart_items.exists():
                return Response({"error": "کارٹ خالی ہے"}, status=400)

            # ٹوٹل پرائس
            total_amount = sum(item.medicine.price * item.quantity for item in cart_items)

            # 2. آرڈر بنائیں
            order = Order.objects.create(
                user=user,
                order_number=str(uuid.uuid4().hex[:10].upper()),
                total_amount=total_amount,
                delivery_address=address,
                status='booked'
            )

            # 3. آئٹمز ٹرانسفر کریں اور اسٹاک کم کریں
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    medicine=item.medicine,
                    quantity=item.quantity,
                    price=item.medicine.price
                )

                # اسٹاک اپ ڈیٹ
                med = item.medicine
                if med.stock_quantity >= item.quantity:
                    med.stock_quantity -= item.quantity
                    med.save()
                else:
                    raise Exception(f"معذرت، {med.name} کا اسٹاک ختم ہو چکا ہے")

            # 4. کارٹ صاف کریں
            cart_items.delete()

            return Response({"success": "آرڈر مکمل ہو گیا!", "order_id": order.order_number}, status=201)

    except Exception as e:
        return Response({"error": str(e)}, status=400)


def order_success_view(request):
    return render(request, 'pharmacy/success.html')