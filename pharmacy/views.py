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
from django.contrib.auth.decorators import login_required
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


@login_required  
def checkout_view(request):
    user = request.user
    try:
    # Get cart 
        cart = Cart.objects.get(user=user)
        cart_items = CartItem.objects.filter(cart=cart)
    except Cart.DoesNotExist:
        cart_items = []

    total = sum(item.medicine.price * item.quantity for item in cart_items)

    context = {
        'user': user, #get user objectے
        'cart_items': cart_items,
        'total': total
    }
    return render(request, 'pharmacy/checkout.html', context)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def place_order(request):
    user = request.user
    address = request.data.get('address') or request.POST.get('address')
    
    if not address:
        return Response({"error": "Please Enter Address"}, status=400)

    try:
        with transaction.atomic():
            # 1. fetch user cart
            cart = get_object_or_404(Cart, user=user)
            cart_items = CartItem.objects.filter(cart=cart)

            if not cart_items.exists():
                return Response({"error": "Cart is empty"}, status=400)

            # Total Price
            total_amount = sum(item.medicine.price * item.quantity for item in cart_items)

            # 2. order
            order = Order.objects.create(
                user=user,
                order_number=str(uuid.uuid4().hex[:10].upper()),
                total_amount=total_amount,
                delivery_address=address,
                status='booked'
            )

            # 3. send item to orderitem table and decrease stock
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    medicine=item.medicine,
                    quantity=item.quantity,
                    price=item.medicine.price
                )

                # update stock
                med = item.medicine
                if med.stock_quantity >= item.quantity:
                    med.stock_quantity -= item.quantity
                    med.save()
                else:
                    raise Exception(f"OutOfStock {med.name}")

            # 4. clean Cart
            cart_items.delete()

            return Response({"success": "Order Completed!", "order_id": order.order_number}, status=201)

    except Exception as e:
        return Response({"error": str(e)}, status=400)


def order_success_view(request):
    return render(request, 'pharmacy/success.html')