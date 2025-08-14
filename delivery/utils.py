from django.db import transaction
from django.db.models import F
from .models import User, Order

def assign_agent_concurrent_safe() -> User | None:
    """
    Pick an available delivery agent fairly and safely under concurrency.
    - Locks the selected row (FOR UPDATE SKIP LOCKED)
    - Prefers agents with lower current_load to spread work
    """
    # IMPORTANT: Must be called inside transaction.atomic()
    # select_for_update with skip_locked prevents race between workers
    agent = (
        User.objects
        .select_for_update(skip_locked=True)
        .filter(user_type="delivery_agent", current_load__lt=F("max_load"))
        .order_by("current_load", "id")
        .first()
    )
    if agent:
        # increment the load so other concurrent txns see updated value
        agent.current_load = F("current_load") + 1
        agent.save(update_fields=["current_load"])
        agent.refresh_from_db(fields=["current_load"])
    return agent


def decrement_agent_load(agent: User):
    if not agent:
        return
    # Use F expression to avoid race on decrement
    User.objects.filter(pk=agent.pk).update(current_load=F("current_load") - 1)
