"""
Give every component its maker's one site name (apps.components.makers), merging
components that turn out to be the same part under two spellings.

    manage.py merge_manufacturers [--dry-run] [--report FILE]

A renamed component keeps its old spelling in manufacturer_aliases (and a moved
part number in alternative_part_numbers). Where the new name and part number
already exist, the two become one: placements, cross-references, images,
datasheets, view counts, requests, recipes, junkbin entries, reports,
suggestions and review rows move to the component kept, which takes any rating,
package or description it lacks from the other. Idempotent.
"""
import csv

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F

from apps.components.makers import canonical_part
from apps.components.models import (Component, ComponentDatasheet, ComponentImage, ComponentViewStats,
                                    ProductComponent, ProductRequest)
from apps.junkbin.models import JunkbinItem
from apps.products.models import ComponentSuggestion, ImportReview
from apps.recipes.models import RecipeComponent
from apps.reports.models import Report
from utils.cache import clear_page_cache


class Command(BaseCommand):
    help = "Rename component makers to the site's spelling and merge the duplicates that makes"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--report', help='write a TSV of every rename and merge')

    def handle(self, *args, **options):
        rows, counts = [], {'renamed': 0, 'merged': 0}
        with transaction.atomic():
            for comp in Component.objects.order_by('created_at'):
                maker, part = canonical_part(comp.manufacturer, comp.part_number)
                if (maker, part) == (comp.manufacturer, comp.part_number):
                    continue
                same = Component.objects.filter(manufacturer__iexact=maker, part_number__iexact=part) \
                    .exclude(pk=comp.pk).first()
                if same:
                    rows.append(['merged', comp.manufacturer, comp.part_number, same.manufacturer, same.part_number,
                                 str(comp.pk), str(same.pk)])
                    merge(comp, same)
                    counts['merged'] += 1
                else:
                    rows.append(['renamed', comp.manufacturer, comp.part_number, maker, part, str(comp.pk), ''])
                    rename(comp, maker, part)
                    counts['renamed'] += 1
            # Crystal Semiconductor's codecs were filed as crystals after the maker's old name
            retyped = Component.objects.filter(manufacturer='Cirrus Logic', component_type='crystal') \
                .update(component_type='ic')
            if options['dry_run']:
                transaction.set_rollback(True)
        if not options['dry_run'] and (counts['renamed'] or counts['merged'] or retyped):
            clear_page_cache()
        if options['report']:
            with open(options['report'], 'w', newline='', encoding='utf-8') as fh:
                out = csv.writer(fh, delimiter='\t')
                out.writerow(['action', 'manufacturer', 'part_number', 'new manufacturer', 'new part_number',
                              'id', 'merged into id'])
                out.writerows(rows)
        prefix = 'DRY RUN - ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}{counts['renamed']} components renamed, {counts['merged']} merged into the same part under "
            f"the site's spelling, {retyped} codecs retyped"))


def _remember(values, old, new):
    return values if old == new or old in values else [*values, old]


def rename(comp, maker, part):
    comp.manufacturer_aliases = _remember(comp.manufacturer_aliases or [], comp.manufacturer, maker)
    comp.alternative_part_numbers = _remember(comp.alternative_part_numbers or [], comp.part_number, part)
    comp.manufacturer, comp.part_number = maker, part
    comp.save()


def merge(dup, keep):
    """Move everything of `dup` onto `keep`, fill what `keep` lacks, delete `dup`."""
    specs = dict(keep.specifications or {})
    for key, value in (dup.specifications or {}).items():
        specs.setdefault(key, value)
    keep.specifications = specs
    for field in ('package_type', 'description', 'typical_function', 'datasheet_url', 'octopart_url'):
        if not getattr(keep, field) and getattr(dup, field):
            setattr(keep, field, getattr(dup, field))
    keep.is_verified = keep.is_verified or dup.is_verified
    keep.manufacturer_aliases = _remember(
        [a for a in (dup.manufacturer_aliases or []) if a not in (keep.manufacturer_aliases or [])]
        + (keep.manufacturer_aliases or []), dup.manufacturer, keep.manufacturer)
    keep.alternative_part_numbers = _remember(
        [a for a in (dup.alternative_part_numbers or []) if a not in (keep.alternative_part_numbers or [])]
        + (keep.alternative_part_numbers or []), dup.part_number, keep.part_number)

    for model in (ProductComponent, ComponentImage, ComponentDatasheet, ProductRequest):
        model.objects.filter(component=dup).update(component=keep)
    ComponentSuggestion.objects.filter(matched_component=dup).update(matched_component=keep)
    for stat in ComponentViewStats.objects.filter(component=dup):
        if not ComponentViewStats.objects.filter(component=keep, date=stat.date).update(
                view_count=F('view_count') + stat.view_count):
            ComponentViewStats.objects.filter(pk=stat.pk).update(component=keep)
    in_recipes = set(RecipeComponent.objects.filter(component=keep).values_list('recipe_id', flat=True))
    RecipeComponent.objects.filter(component=dup, recipe_id__in=in_recipes).delete()
    RecipeComponent.objects.filter(component=dup).update(component=keep)

    through = Component.cross_references.through
    others = (set(through.objects.filter(from_component=dup).values_list('to_component_id', flat=True))
              | set(through.objects.filter(to_component=dup).values_list('from_component_id', flat=True)))
    keep.cross_references.add(*Component.objects.filter(pk__in=others - {keep.pk, dup.pk}))

    ct = ContentType.objects.get_for_model(Component)
    for item in JunkbinItem.objects.filter(content_type=ct, object_id=str(dup.pk)):
        if JunkbinItem.objects.filter(user=item.user, content_type=ct, object_id=str(keep.pk),
                                      item_type=item.item_type).exists():
            item.delete()
        else:
            JunkbinItem.objects.filter(pk=item.pk).update(object_id=str(keep.pk))
    Report.objects.filter(content_type=ct, object_id=str(dup.pk)).update(object_id=str(keep.pk))
    for review in ImportReview.objects.filter(item_type='component', object_id=str(dup.pk)):
        if ImportReview.objects.filter(batch=review.batch, item_type='component', object_id=str(keep.pk)).exists():
            review.delete()
        else:
            ImportReview.objects.filter(pk=review.pk).update(object_id=str(keep.pk))

    dup.delete()
    keep.save()
    keep.update_usage_count()
