"""
Celery tasks for component enrichment via Nexar API.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def enrich_component(self, component_id):
    """
    Fetch pricing, availability, and datasheet data from Nexar
    for a single component. Stores result in specifications['nexar_data'].
    """
    from .models import Component
    from .nexar import get_client

    try:
        component = Component.objects.get(pk=component_id)
    except Component.DoesNotExist:
        logger.warning("Component %s not found, skipping enrichment", component_id)
        return

    client = get_client()
    if not client.is_configured:
        logger.info("Nexar API not configured, skipping enrichment")
        return

    try:
        result = client.search_mpn(component.part_number, component.manufacturer)
    except Exception as exc:
        logger.exception("Nexar lookup failed for %s", component.part_number)
        raise self.retry(exc=exc)

    if not result:
        logger.info("No Nexar results for %s %s", component.manufacturer, component.part_number)
        return

    # Store enrichment data
    specs = component.specifications or {}
    specs["nexar_data"] = {
        **result,
        "last_updated": timezone.now().isoformat(),
    }
    component.specifications = specs

    # Auto-fill datasheet if empty
    if not component.datasheet_url and result.get("datasheet_url"):
        component.datasheet_url = result["datasheet_url"]

    # Auto-fill octopart_url
    if not component.octopart_url and result.get("mpn"):
        component.octopart_url = f"https://octopart.com/search?q={result['mpn']}"

    # Auto-fill description from Nexar's category text if empty
    if not component.description and result.get("description"):
        component.description = result["description"]

    component.save(update_fields=["specifications", "datasheet_url", "octopart_url", "description"])
    logger.info("Enriched component %s with Nexar data", component.part_number)


@shared_task
def bulk_enrich_components(limit=50):
    """
    Enrich components that have no nexar_data yet.
    Intended for periodic (nightly) runs via celery-beat.
    """
    from .models import Component

    components = (
        Component.objects
        .exclude(specifications__has_key="nexar_data")
        .order_by("-usage_count")[:limit]
    )

    count = 0
    for comp in components:
        enrich_component.delay(str(comp.pk))
        count += 1

    logger.info("Queued %d components for Nexar enrichment", count)
    return count
