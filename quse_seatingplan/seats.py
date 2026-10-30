from django.db import transaction
from pretix.base.models import Event, SeatCategoryMapping
from pretix.base.services import seating as seating_service


def mapping_for(event, subevent):
    rows = SeatCategoryMapping.objects.filter(event=event, subevent=subevent)
    if subevent and not rows.exists():
        rows = SeatCategoryMapping.objects.filter(event=event, subevent=None)
    mapping = {}
    for row in rows:
        # pretix generate_seats accepts a category mapping only when the
        # category has an unambiguous product.
        if row.product_id:
            if row.layout_category in mapping:
                mapping[row.layout_category] = None
            else:
                mapping[row.layout_category] = row.product
    return {category: product for category, product in mapping.items() if product}


def ensure_subevent_seats(event, subevent):
    """Create a date's seats once, preserving any seats already in use."""
    plan = subevent.seating_plan or event.seating_plan
    if not plan:
        return
    with transaction.atomic():
        # Serialize first-time initialization across checkout requests.
        Event.objects.select_for_update().get(pk=event.pk)
        if event.seats.filter(subevent=subevent).exists():
            return
        seating_service.generate_seats(
            event, subevent, plan, mapping_for(event, subevent)
        )
