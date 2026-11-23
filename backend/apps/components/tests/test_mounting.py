"""The mounting a board implies for a part whose line names no package, and the backfill command."""
import pytest
from django.core.management import call_command
from io import StringIO

from apps.components.models import Component, ProductComponent
from apps.components.mounting import mount_default

pytestmark = pytest.mark.django_db


def test_mainboard_chips_are_smd_but_electrolytics_and_crystals_are_not_named():
    assert mount_default('schematic-bom:msi-ms-7500-0d', 'resistor') == 'SMD'
    assert mount_default('schematic-bom:asus-f8va', 'capacitor', {'capacitance_pf': 100000.0}) == 'SMD'
    assert mount_default('schematic-bom:msi-ms-7500-0d', 'capacitor', {'capacitance_pf': 1e9}) == ''
    assert mount_default('schematic-bom:msi-ms-7500-0d', 'capacitor', {}) == ''
    assert mount_default('schematic-bom:msi-ms-7500-0d', 'crystal') == ''


def test_amplifier_resistors_and_diodes_are_axial_and_the_rest_unnamed():
    assert mount_default('schematicheaven:Fender_Twin', 'resistor') == 'Axial'
    assert mount_default('schematicheaven:Fender_Twin', 'diode') == 'Axial'
    assert mount_default('schematicheaven:Fender_Twin', 'capacitor', {'capacitance_pf': 100.0}) == ''
    assert mount_default('norway-svc:Sharp_LC-42SD1E', 'resistor') == ''
    assert mount_default('', 'resistor') == ''


def _place(comp, product, src, ref):
    ProductComponent.objects.create(component=comp, product=product, reference_designator=ref, import_source=src)


def test_fill_command_labels_only_parts_whose_boards_agree(product_factory):
    amp, board, tv = product_factory(), product_factory(), product_factory()
    axial = Component.objects.create(manufacturer='Generic', part_number='RES 100K', component_type='resistor')
    smd = Component.objects.create(manufacturer='Generic', part_number='RES 10K', component_type='resistor')
    shared = Component.objects.create(manufacturer='Generic', part_number='RES 1K', component_type='resistor')
    unplaced = Component.objects.create(manufacturer='Generic', part_number='RES 2K', component_type='resistor')
    sized = Component.objects.create(manufacturer='Generic', part_number='RES 3K', component_type='resistor', package_type='0603')
    _place(axial, amp, 'schematicheaven:Fender_Twin', 'R1')
    _place(smd, board, 'schematic-bom:asus-f8va', 'R2')
    _place(shared, amp, 'schematicheaven:Fender_Twin', 'R3')
    _place(shared, tv, 'norway-svc:Sharp_LC-42SD1E', 'R4')
    out = StringIO()
    call_command('fill_mount_packages', stdout=out)
    assert 'DRY RUN' in out.getvalue() and 'resistor -> Axial 1' in out.getvalue() and 'resistor -> SMD 1' in out.getvalue()
    assert Component.objects.get(pk=axial.pk).package_type == ''
    call_command('fill_mount_packages', '--apply', stdout=out)
    assert Component.objects.get(pk=axial.pk).package_type == 'Axial'
    assert Component.objects.get(pk=smd.pk).package_type == 'SMD'
    assert Component.objects.get(pk=shared.pk).package_type == ''
    assert Component.objects.get(pk=unplaced.pk).package_type == ''
    assert Component.objects.get(pk=sized.pk).package_type == '0603'
