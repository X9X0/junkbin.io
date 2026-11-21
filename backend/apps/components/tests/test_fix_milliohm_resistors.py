"""fix_milliohm_resistors: a '470m' read as 470 MΩ goes back to 0.47 Ω, placement by placement, on the note's own word."""
import io

import pytest
from django.core.management import call_command

from apps.components.management.commands.fix_milliohm_resistors import note_value, sub_ohm_name
from apps.components.models import Component, ProductComponent
from apps.products.models import Product

pytestmark = pytest.mark.django_db


def test_the_note_states_the_true_value():
    assert note_value('Output emitters (.47 2W). Read from Kay model 771 schematic') == 0.47
    assert note_value('Output emitters (0,1E). Read from AB Albin Hagstrom') == 0.1
    assert note_value('Output emitters (0.5/2W). Read from MS Music Service') == 0.5
    assert note_value('Factory BOM line: RES 100m OHM 1/4W (1206) 5%; approved makers: TA-I') == 0.1
    assert note_value("schematic label '3m 2W'") is None                    # a bare label does not say what it is
    assert note_value("schematic label '0R 100M'") is None
    assert note_value('Grid leak (1.5 MEG). Read from Harmony schematic') is None
    assert note_value('Read from Yorkville operating instructions (English and French; 80 W RMS) and a table (0.1 % distortion)') is None
    assert sub_ohm_name('RES 470M 2W', 0.47) == 'RES 0.47R 2W'
    assert sub_ohm_name('RES 500M 2W 2W', 0.5) == 'RES 0.5R 2W'
    assert sub_ohm_name('RES 100M 5% 1/4W 1206', 0.1) == 'RES 0.1R 5% 1/4W 1206'


def _product(name):
    return Product.objects.create(manufacturer='Standel', model_number=name, category='instrument_amp')


def test_rename_merge_and_split(user_factory):
    wrong = Component.objects.create(manufacturer='Generic', part_number='RES 470M 2W', component_type='resistor', description='Resistor 470M, 2W',
                                     specifications={'power_w': 2.0, 'resistance_ohm': 470e6})
    ProductComponent.objects.create(product=_product('Studio Reverb'), component=wrong, reference_designator='R11', quantity=2, notes='Output emitters (.47 2W). Read from Standel service information')
    # merge: the right part exists already, with one placement that would duplicate a moved one
    wrong5 = Component.objects.create(manufacturer='Generic', part_number='RES 270M 5W', component_type='resistor', specifications={'resistance_ohm': 270e6})
    right5 = Component.objects.create(manufacturer='Generic', part_number='RES 0.27R 5W', component_type='resistor', specifications={'resistance_ohm': 0.27})
    tr75 = _product('TR 75GT')
    ProductComponent.objects.create(product=tr75, component=wrong5, reference_designator='R22', notes='Output emitters (.27 5W). Read from Rickenbacker TR 75GT schematic')
    ProductComponent.objects.create(product=tr75, component=right5, reference_designator='R22', notes='already there')
    ProductComponent.objects.create(product=_product('TR 7'), component=wrong5, reference_designator='R9', notes='Output emitters (0.27 5W). Read from Rickenbacker TR 7')
    # split: one part carries both a real 0.1 Ω reading and label noise that stays
    mixed = Component.objects.create(manufacturer='Generic', part_number='RES 100M', component_type='resistor', specifications={'resistance_ohm': 100e6})
    ProductComponent.objects.create(product=_product('Mod 170'), component=mixed, reference_designator='R30', notes='Output emitters (0,1E). Read from AB Albin Hagstrom, Mod 170')
    ProductComponent.objects.create(product=_product('Laptop'), component=mixed, reference_designator='R1', notes="schematic label '0R 100M'")
    # untouched: a real megohm part
    big = Component.objects.create(manufacturer='Generic', part_number='RES 1.5M', component_type='resistor', specifications={'resistance_ohm': 1.5e6})
    ProductComponent.objects.create(product=_product('H306'), component=big, notes='Grid leaks (1.5Meg). Read from Harmony schematic')

    out = io.StringIO(); call_command('fix_milliohm_resistors', stdout=out)
    assert 'DRY RUN' in out.getvalue() and Component.objects.filter(part_number='RES 470M 2W').exists()
    out = io.StringIO(); call_command('fix_milliohm_resistors', '--apply', stdout=out)
    text = out.getvalue()
    assert 'renamed 1' in text and 'merged 1' in text and 'split 1' in text and 'duplicates dropped 1' in text

    wrong.refresh_from_db()
    assert wrong.part_number == 'RES 0.47R 2W' and wrong.specifications['resistance_ohm'] == 0.47 and wrong.description == 'Resistor 0.47R, 2W'
    assert not Component.objects.filter(part_number='RES 270M 5W').exists()
    right5.refresh_from_db()
    assert right5.usage_count == 2 and set(right5.product_components.values_list('reference_designator', flat=True)) == {'R22', 'R9'}
    mixed.refresh_from_db()
    new = Component.objects.get(part_number='RES 0.1R')
    assert new.specifications['resistance_ohm'] == 0.1 and new.usage_count == 1
    assert mixed.usage_count == 1 and mixed.product_components.get().reference_designator == 'R1'
    big.refresh_from_db()
    assert big.part_number == 'RES 1.5M'
