from django.db import models
from django.conf import settings


# category table
class MedicineCategory(models.Model):
    name = models.CharField(max_length=100,unique=True)
    description = models.TextField(blank=True)

    # Add this to show the name in Admin
    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Medicine Categories"


# medicine table
class Medicine(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(MedicineCategory, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField()
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='medicines/', null=True, blank=True)

# Add this to show the medicine name in Admin
    def __str__(self):
        return self.name



# cart table
class Cart(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user.username}"


# cartItem Table
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    def __str__(self):
        return f"{self.medicine.name} in {self.cart.user.username}'s Cart"


# Order Table
class Order(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=20, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    STATUS_CHOICES = (
        ('booked', 'booked'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='booked')
#   payment_method = models.CharField(max_length=50, blank=True, null=True)
    delivery_address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Order {self.order_number} by {self.user.username}"

#  OrderItem Table
class OrderItem(models.Model):

    order = models.ForeignKey('Order',on_delete=models.CASCADE,related_name='items')
    medicine = models.ForeignKey('Medicine',on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10,decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def subtotal(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.medicine.name} x {self.quantity}"