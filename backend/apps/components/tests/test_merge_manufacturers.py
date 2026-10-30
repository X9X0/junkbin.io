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
    assert canonical_maker('ENTRY') == canonical_maker('ENTERY') == 'Entery'
    assert canonical_maker('NIKE') == canonical_maker('NIKETECH') == 'Niketech'
    assert canonical_maker('Some New Maker') == 'Some New Maker'
    assert canonical_part('JVE21R2264-10S10-01G-6', '3-V1-GN') == ('JVE', '21R2264-10S10-01G-6/3-V1-GN')
    assert canonical_part('Generic', 'T49J NUT H=4.0mm 宏泰') == ('Generic', 'T49J NUT H=4.0mm Hontech')
    assert canonical_part('Generic', 'WAFER HD 4P S/T 2.54mm,WHITE 小4P') == \
        ('Generic', 'WAFER HD 4P S/T 2.54mm,WHITE small 4-pin')
    assert canonical_part('Vette', '10ADAI 宏泰') == ('Vette', '10ADAI 宏泰')     # a maker's own number is kept


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


def test_generic_line_name_is_translated(component_factory, product_factory):
    english = component_factory(manufacturer='Generic', part_number='T12 MB RJ45 SPONGE Shang Yi')
    chinese = component_factory(manufacturer='Generic', part_number='T12 MB RJ45 SPONGE 上藝')
    lone = component_factory(manufacturer='Generic', part_number='HEATSINK FOR K8 VRM 國格')
    ProductComponent.objects.create(product=product_factory(), component=chinese, reference_designator='M1')
    assert '1 components renamed, 1 merged' in _run()
    assert english.product_components.count() == 1
    lone.refresh_from_db()
    assert lone.part_number == 'HEATSINK FOR K8 VRM KG' and lone.alternative_part_numbers == ['HEATSINK FOR K8 VRM 國格']


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


def test_product_brands_take_a_leading_capital(product_factory):
    from apps.components.makers import canonical_product_maker
    from apps.products.models import Product
    assert canonical_product_maker('ASUS') == 'Asus' and canonical_product_maker('UNI-T') == 'Uni-T'
    assert canonical_product_maker('MSI') == 'MSI' and canonical_product_maker('HP') == 'HP'   # acronyms stay
    board = product_factory(manufacturer='ASUS', model_number='P5K', revision='1.02G')
    slug = board.slug
    taken = product_factory(manufacturer='GIGABYTE', model_number='GA-X', revision='1.0')
    product_factory(manufacturer='Gigabyte', model_number='GA-X', revision='1.0')
    assert '1 product makers respelled' in _run()
    board.refresh_from_db()
    taken.refresh_from_db()
    assert (board.manufacturer, board.slug) == ('Asus', slug)           # same page address
    assert taken.manufacturer == 'GIGABYTE'                             # the new spelling is taken: left alone
    assert Product.objects.filter(manufacturer='Asus').count() == 1
