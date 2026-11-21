"""merge_sized_twins: one machine under a plain and a sized name becomes the sized page with everything moved over."""
from io import StringIO

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command

from apps.components.models import Component, ProductComponent
from apps.junkbin.models import JunkbinItem
from apps.products.models import Firmware, Product, ProductImage, ProductLink

pytestmark = pytest.mark.django_db


def product(brand, model, src='norway-fw:test', category='laptop', approved=True):
    return Product.objects.create(manufacturer=brand, model_number=model, category=category, import_source=src,
                                  is_approved=approved, description='x')


def test_the_sized_spelling_survives_with_everything_moved(user_factory):
    for m in ('Inspiron 5567', 'Inspiron 7567'):
        product('Dell', m)
    plain = product('Dell', 'Inspiron 3542')
    dashed = product('Dell', 'Inspiron 15-3542')
    spaced = product('Dell', 'Inspiron 15 3542', approved=False)
    other = product('Dell', 'Inspiron 13-5368')                     # a different size: not in the group
    board = product('Compal', 'LA-B303P', src='norway-board:Compal_LA-B303P_1.0', category='other')
    ProductLink.objects.create(part=board, host=plain, kind='fitted_in', import_source='t', is_approved=True)
    ProductLink.objects.create(part=board, host=spaced, kind='fitted_in', import_source='t')   # twin: dropped, approval kept
    Firmware.objects.create(product=plain, title='dump A', file='fw/a.bin')
    Firmware.objects.create(product=dashed, title='dump B', file='fw/b.bin')
    ProductImage.objects.create(product=plain, image='img/a.jpg', is_primary=True)
    ProductImage.objects.create(product=spaced, image='img/b.jpg', is_primary=True)
    cap = Component.objects.create(manufacturer='Murata', part_number='GRM1', component_type='capacitor')
    ProductComponent.objects.create(product=plain, component=cap, reference_designator='C1', quantity=1)
    ProductComponent.objects.create(product=spaced, component=cap, reference_designator='C1', quantity=1)   # duplicate
    user = user_factory()
    JunkbinItem.objects.create(user=user, content_type=ContentType.objects.get_for_model(Product), object_id=plain.pk,
                               item_type='have')
    out = StringIO()
    call_command('merge_sized_twins', verbose=True, stdout=out)
    assert not Product.objects.filter(pk__in=[plain.pk, dashed.pk]).exists()
    spaced.refresh_from_db()
    assert spaced.is_approved                                             # an approved twin makes the survivor approved
    assert Product.objects.filter(pk=other.pk).exists()
    assert set(Firmware.objects.filter(product=spaced).values_list('title', flat=True)) == {'dump A', 'dump B'}
    assert spaced.images.count() == 2 and spaced.images.get(is_primary=True).image == 'img/b.jpg'
    assert ProductComponent.objects.filter(product=spaced).count() == 1
    link = ProductLink.objects.get(part=board, host=spaced)
    assert link.is_approved
    assert JunkbinItem.objects.get(user=user).object_id == spaced.pk
    assert 'merged 2' in out.getvalue()
    out = StringIO()
    call_command('merge_sized_twins', stdout=out)
    assert out.getvalue().strip() == 'nothing to merge'
