"""
Tests for manage.py merge_manufacturers and the maker spellings.
"""
from io import StringIO

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command

from apps.components.makers import canonical_maker, canonical_part
from apps.components.models import Component, ProductComponent
from apps.junkbin.models import JunkbinItem

pytestmark = pytest.mark.django_db


def _run(*args):
    out = StringIO()
    call_command('merge_manufacturers', *args, stdout=out)
    return out.getvalue()


def test_spellings():
    assert canonical_maker('YAGEO') == canonical_maker('Yageo') == 'Yageo'
    assert canonical_maker('TA-I TECH') == canonical_maker('TA-ITECH') == 'TA-I'
    assert canonical_maker('TAI TECH') == 'Tai-Tech'
    assert canonical_maker('TDK') == 'TDK' and canonical_maker('KOA') == 'KOA'      # acronyms stay
    assert canonical_maker('MAG.LAYERS') == canonical_maker('MAG LAYERS') == 'Mag Layers'
    assert canonical_maker('Some New Maker') == 'Some New Maker'
    assert canonical_part('JVE21R2264-10S10-01G-6', '3-V1-GN') == ('JVE', '21R2264-10S10-01G-6/3-V1-GN')


def test_rename_keeps_the_old_spelling_as_an_alias(component_factory):
    part = component_factory(manufacturer='SUYIN', part_number='254301MS010G275UO', manufacturer_aliases=[])
    _run()
    part.refresh_from_db()
    assert part.manufacturer == 'Suyin' and part.manufacturer_aliases == ['SUYIN']


def test_same_part_under_two_spellings_becomes_one(component_factory, product_factory, user_factory):
    keep = component_factory(manufacturer='Yageo', part_number='RC0402JR-0710KL', package_type='',
                             specifications={'resistance_ohm': 10000.0}, manufacturer_aliases=[])
    dup = component_factory(manufacturer='YAGEO', part_number='RC0402JR-0710KL', package_type='0402',
                            specifications={'resistance_ohm': 10000.0, 'tolerance': '5%'}, manufacturer_aliases=[])
    other = component_factory(manufacturer='Walsin', part_number='WR04X103JTL')
    dup.cross_references.add(other)
    ProductComponent.objects.create(product=product_factory(), component=dup, reference_designator='R1')
    user = user_factory()
    ct = ContentType.objects.get_for_model(Component)
    JunkbinItem.objects.create(user=user, content_type=ct, object_id=dup.pk, item_type='have')
    assert '1 merged' in _run()
    assert not Component.objects.filter(pk=dup.pk).exists()
    keep.refresh_from_db()
    assert keep.package_type == '0402' and keep.specifications['tolerance'] == '5%'
    assert keep.manufacturer_aliases == ['YAGEO']
    assert list(keep.cross_references.all()) == [other]
    assert keep.product_components.count() == 1 and keep.usage_count == 1
    assert JunkbinItem.objects.get(user=user).object_id == keep.pk
    assert '0 components renamed, 0 merged' in _run()          # idempotent


def test_dry_run_changes_nothing(component_factory):
    part = component_factory(manufacturer='TOPYANG', part_number='111240-A0C000T')
    assert _run('--dry-run').startswith('DRY RUN - 1 components renamed')
    part.refresh_from_db()
    assert part.manufacturer == 'TOPYANG'


def test_new_component_takes_the_sites_spelling(api_client, user_factory):
    api_client.force_authenticate(user_factory())
    response = api_client.post('/api/components/', {'manufacturer': 'YAGEO', 'part_number': 'RC0603FR-0710KL',
                                                    'component_type': 'resistor'}, format='json')
    assert response.status_code == 201, response.content
    assert Component.objects.get(part_number='RC0603FR-0710KL').manufacturer == 'Yageo'
