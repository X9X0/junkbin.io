"""
tidy_generic_names removes the extractor's value-named chip misreads and merges
off-convention Generic names into the engine's.
"""
from io import StringIO

import pytest
from django.core.management import call_command

from apps.components.models import Component, ProductComponent

pytestmark = pytest.mark.django_db


def _place(product, component, designator, source):
    return ProductComponent.objects.create(product=product, component=component, reference_designator=designator,
                                           quantity=1, import_source=source)


def _run(*args):
    out = StringIO()
    call_command('tidy_generic_names', *args, stdout=out)
    return out.getvalue()


def test_misreads_go_but_hand_written_values_and_real_chips_stay(product_factory, component_factory):
    board = product_factory(manufacturer='ASUS', model_number='A6KM', is_approved=True)
    amp = product_factory(manufacturer='Fender', model_number='Champ', is_approved=True)
    misread = component_factory(manufacturer='Generic', part_number='680Ohm', component_type='diode')
    zener = component_factory(manufacturer='Generic', part_number='15V', component_type='diode')
    real = component_factory(manufacturer='Generic', part_number='W83627F', component_type='ic')
    _place(board, misread, 'D8', 'schematic-bom:asus-a6km')
    _place(board, misread, 'U2', 'schematic-bom:asus-a6km')
    _place(board, real, 'U7', 'schematic-bom:asus-a6km')
    _place(amp, zener, 'D1', 'schematicheaven:Fender_Champ')         # a repairer's shorthand: kept
    board.update_component_count()

    out = _run('--dry-run')
    assert 'DRY RUN' in out and ProductComponent.objects.filter(component=misread).count() == 2

    out = _run()
    assert 'misread placements removed 2, components removed 1 (680Ohm)' in out
    assert not Component.objects.filter(part_number='680Ohm').exists()
    assert ProductComponent.objects.filter(component=zener).count() == 1 and Component.objects.filter(pk=zener.pk).exists()
    assert ProductComponent.objects.filter(component=real).count() == 1
    board.refresh_from_db()
    assert board.component_count == 1


def test_off_convention_names_merge_into_the_engines(product_factory, component_factory):
    amiga = product_factory(manufacturer='Commodore', model_number='CDTV', is_approved=True)
    old = component_factory(manufacturer='Generic', part_number='32.768 kHz crystal', component_type='crystal')
    new = component_factory(manufacturer='Generic', part_number='XTAL 32.768kHz', component_type='crystal')
    _place(amiga, old, 'X2', 'amiga-docs:CDTV')

    out = _run()
    assert "merged '32.768 kHz crystal' into 'XTAL 32.768kHz': 1 placement(s)" in out
    assert not Component.objects.filter(pk=old.pk).exists()
    row = ProductComponent.objects.get(product=amiga, reference_designator='X2')
    assert row.component == new
    new.refresh_from_db()
    assert new.usage_count == 1
