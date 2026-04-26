# pharmacy/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicineViewSet, CartViewSet,CategoryViewSet,cart_count,checkout_view,place_order,order_success_view

# 1. Initialize the router
router = DefaultRouter()

# 2. Register your viewsets
# Note: Since these are in the pharmacy app, we don't need 'api/' in the prefix here
router.register(r'medicines', MedicineViewSet, basename='medicines')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'cart', CartViewSet, basename='cart')

# 3. Define the urlpatterns for this app
urlpatterns = [
    path('', include(router.urls)),
        path('cart/count/', cart_count, name='cart_count'),
        path('checkout/', checkout_view, name='checkout_page'),
      

    # 2. یہ وہ URL ہے جہاں AJAX کے ذریعے آرڈر سیو ہونے کے لیے جائے گا
    path('place-order/', place_order, name='place_order_api'),
    
    # 3. آرڈر کامیاب ہونے کے بعد ری ڈائریکٹ کرنے کے لیے ایک پیج
     path('order-success/', order_success_view, name='order_success'),


]