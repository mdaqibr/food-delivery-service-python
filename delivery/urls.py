from django.urls import path
from . import views

urlpatterns = [
    path("users", views.register),
    path("restaurants", views.create_restaurant),
    path("place-order", views.place_order),
    path("orders", views.get_all_orders),
    path("orders/<int:id>", views.get_order),
    path("accept-order", views.accept_order),
    path("mark-delivered", views.mark_delivered),
    path("order-history/<int:user_id>", views.order_history),
    path("restaurants/<int:id>", views.restaurant_details),
]
