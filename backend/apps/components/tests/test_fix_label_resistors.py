"""fix_label_resistors: a label whose value token was a clock net or a chip name goes to the part the sheet shows."""
import io

import pytest
from django.core.management import call_command

from apps.components.models import Component, ProductComponent
from apps.products.models import Product

pytestmark = pytest.mark.django_db


def test_clock_net_labels_move_and_chip_labels_go(user_factory):
    board = Product.objects.create(manufacturer='Asus', model_number='Z96JM', category='laptop')
    wrong48 = Component.objects.create(manufacturer='Generic', part_number='RES 48M', component_type='resistor', specifications={'resistance_ohm': 48e6})
    ProductComponent.objects.create(product=board, component=wrong48, reference_designator='R285', notes="schematic label '_CLK_48M'")
    wrong16 = Component.objects.create(manufacturer='Generic', part_number='RES 16M', component_type='resistor', specifications={'resistance_ohm': 16e6})
    ProductComponent.objects.create(product=board, component=wrong16, reference_designator='RN50', notes="schematic label '16M'")
    unsettled = Component.objects.create(manufacturer='Generic', part_number='RES 66M', component_type='resistor', specifications={'resistance_ohm': 66e6})
    ProductComponent.objects.create(product=board, component=unsettled, reference_designator='R4', notes="schematic label '66M_NB'")
    fine = Component.objects.create(manufacturer='Generic', part_number='RES 10M 0603', component_type='resistor', specifications={'resistance_ohm': 10e6})
    ProductComponent.objects.create(product=board, component=fine, reference_designator='R688', notes="schematic label '10M/6 OSC32KHO'")
    excluded_board = Product.objects.create(manufacturer='Asus', model_number='T75AL2', category='laptop')
    three = Component.objects.create(manufacturer='Generic', part_number='RES 3M', component_type='resistor', specifications={'resistance_ohm': 3e6})
    ProductComponent.objects.create(product=excluded_board, component=three, reference_designator='R390', notes="schematic label '3m'")

    out = io.StringIO(); call_command('fix_label_resistors', stdout=out)
    assert 'DRY RUN' in out.getvalue() and Component.objects.filter(part_number='RES 48M').exists()
    out = io.StringIO(); call_command('fix_label_resistors', '--apply', stdout=out)
    text = out.getvalue()
    assert 'placements moved 1' in text and 'placements deleted 1' in text and 'left unsettled 1' in text and 'excluded 1' in text

    moved = ProductComponent.objects.get(reference_designator='R285')
    assert moved.component.part_number == 'RES 33R' and moved.component.specifications['resistance_ohm'] == 33
    assert '48 MHz' in moved.notes and moved.notes.startswith("schematic label '_CLK_48M'")
    assert not Component.objects.filter(part_number__in=['RES 48M', 'RES 16M']).exists()
    assert not ProductComponent.objects.filter(reference_designator='RN50').exists()
    assert ProductComponent.objects.get(reference_designator='R4').component == unsettled
    assert ProductComponent.objects.get(reference_designator='R688').component == fine
    assert ProductComponent.objects.get(reference_designator='R390').component == three
