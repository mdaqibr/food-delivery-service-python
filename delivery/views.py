from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from django.http import JsonResponse

from rest_framework.decorators import api_view
from rest_framework import status

from django.core.cache import cache

from .models import User, Restaurant, Order, OrderItem
from .serializers import UserSerializer, RestaurantSerializer, OrderSerializer
from .utils import assign_agent_concurrent_safe, decrement_agent_load

# Registration (unchanged)
@api_view(["POST"])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Create Restaurant (simple write-through)
@api_view(["POST"])
def create_restaurant(request):
    serializer = RestaurantSerializer(data=request.data)
    if serializer.is_valid():
        rest = serializer.save()
        # Bust any cache that may depend on restaurants list/details
        cache.delete_pattern("restaurant:*")
        return Response(RestaurantSerializer(rest).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Place Order (auto-assign!)
@api_view(["POST"])
def place_order(request):
    """
    Creates Order + OrderItems inside a single DB transaction
    and auto-assigns a delivery agent safely under concurrency.
    """
    serializer = OrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    items_data = data.pop("items", [])
    user = get_object_or_404(User, pk=request.data.get("user"), user_type="customer")
    restaurant = get_object_or_404(Restaurant, pk=request.data.get("restaurant"))

    with transaction.atomic():
        # 1) Lock and assign agent (may be None if all at max_load)
        agent = assign_agent_concurrent_safe()

        # 2) Create order
        order = Order.objects.create(
            user=user,
            restaurant=restaurant,
            agent=agent,
            status="pending",
            total_price=request.data.get("total_price"),
        )

        # 3) Create items
        bulk_items = [
            OrderItem(order=order, **item) for item in items_data
        ]
        OrderItem.objects.bulk_create(bulk_items)

    # Invalidate order-history cache for this user
    cache.delete(f"order_history:{user.id}")

    out = OrderSerializer(order)
    return Response(out.data, status=status.HTTP_201_CREATED)


# Accept Order (agent lock)
@api_view(["POST"])
def accept_order(request):
    """
    Agent accepts an order. We ensure only valid transitions.
    """
    order_id = request.data.get("order_id")
    agent_id = request.data.get("agent_id")

    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), pk=order_id)

        if order.status != "pending":
            return Response({"error": "Order not in pending state."}, status=400)

        agent = get_object_or_404(User.objects.select_for_update(), pk=agent_id, user_type="delivery_agent")

        # If order was auto-assigned, ensure it's same agent OR allow takeover if none
        if order.agent and order.agent_id != agent.id:
            return Response({"error": "Order already assigned to another agent."}, status=400)

        # Ensure capacity for the agent
        if agent.current_load >= agent.max_load:
            return Response({"error": "Agent is at full capacity."}, status=400)

        order.agent = agent
        order.status = "accepted"
        order.save(update_fields=["agent", "status"])

        # Increase load if agent wasn't already the assigned one
        if not order.agent_id or order.agent_id == agent.id:
            agent.current_load = F("current_load") + 1
            agent.save(update_fields=["current_load"])

    return Response({"message": "Order accepted"}, status=200)

@api_view(["GET"])
def get_all_orders(request):
    """Fetch all orders with details"""
    orders = Order.objects.select_related("user", "restaurant", "agent").all()
    data = []
    for o in orders:
        data.append({
            "id": o.id,
            "customer": o.user.name,
            "restaurant": o.restaurant.name,
            "agent": o.agent.name if o.agent else None,
            "status": o.status,
        })
    return JsonResponse({"orders": data}, status=200)

@api_view(["GET"])
def get_order(request, id):
    if request.method == "GET":
        try:
            order = Order.objects.get(id=id)
            data = {
                "id": order.id,
                "user": order.user.name,
                "restaurant": order.restaurant.name,
                "agent": order.agent.name if order.agent else None,
                "status": order.status,
            }
            return JsonResponse(data, safe=False)
        except Order.DoesNotExist:
            return JsonResponse({"error": "Order not found"}, status=404)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


# Mark Delivered (decrement)
@api_view(["POST"])
def mark_delivered(request):
    order_id = request.data.get("order_id")
    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), pk=order_id)

        # Allow delivered from accepted or in_transit for simplicity
        if order.status not in ("accepted", "in_transit"):
            return Response({"error": f"Cannot deliver from '{order.status}' state."}, status=400)

        order.status = "delivered"
        order.save(update_fields=["status"])

        # Agent load goes down
        decrement_agent_load(order.agent)

        # Invalidate order-history cache
        cache.delete(f"order_history:{order.user_id}")

    return Response({"message": "Order delivered"}, status=200)


# Order History (cached)
@api_view(["GET"])
def order_history(request, user_id):
    cache_key = f"order_history:{user_id}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    orders = (
        Order.objects
        .filter(user_id=user_id)
        .select_related("restaurant", "agent")
        .prefetch_related("items")
        .order_by("-created_at")
    )
    data = OrderSerializer(orders, many=True).data
    cache.set(cache_key, data, timeout=60)  # cache for 60s (tune as needed)
    return Response(data)


# Restaurant Details (cached)
@api_view(["GET"])
def restaurant_details(request, id):
    cache_key = f"restaurant:{id}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    try:
        restaurant = Restaurant.objects.get(id=id)
    except Restaurant.DoesNotExist:
        return Response({"error": "Restaurant not found"}, status=404)

    data = RestaurantSerializer(restaurant).data
    cache.set(cache_key, data, timeout=300)  # 5 min cache
    return Response(data)
