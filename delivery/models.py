from django.db import models
from django.utils import timezone

class User(models.Model):
    USER_TYPES = (
        ("customer", "Customer"),
        ("delivery_agent", "Delivery Agent"),
    )
    name = models.CharField(max_length=100, db_index=True)
    mobile = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, db_index=True)

    # Fields used only when user_type == delivery_agent
    current_load = models.PositiveIntegerField(default=0, db_index=True)  # active orders
    max_load = models.PositiveIntegerField(default=3)  # capacity (can be tuned)

    def __str__(self):
        return f"{self.name} ({self.user_type})"

    class Meta:
        indexes = [
            models.Index(fields=["user_type", "current_load"]),
            models.Index(fields=["name"]),
        ]


class Restaurant(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    location = models.CharField(max_length=255)
    rating = models.FloatField(default=0.0, db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=["rating"]),
        ]


class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("in_transit", "In Transit"),
        ("delivered", "Delivered"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders", db_index=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, db_index=True)
    agent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries",
        limit_choices_to={"user_type": "delivery_agent"},
        db_index=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["restaurant", "created_at"]),
        ]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", db_index=True)
    item_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField()
