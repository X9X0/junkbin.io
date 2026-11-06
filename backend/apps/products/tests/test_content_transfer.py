"""export_content on one site, load_content on another: imported content arrives with its
review state, beside the other site's own rows."""
import datetime
import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.components.models import Component, ComponentDatasheet, ProductComponent
from apps.products.models import ImportReview, Product, ProductImage, Schematic

SINCE = (timezone.now() - datetime.timedelta(days=1)).date().isoformat()


MADE = timezone.now() - datetime.timedelta(hours=12)       # when the exporting site made its rows


def _old(obj):
    type(obj).objects.filter(pk=obj.pk).update(created_at=timezone.now() - datetime.timedelta(days=30))


def _made(obj):
    field = 'created_at' if hasattr(obj, 'created_at') else 'uploaded_at'
    type(obj).objects.filter(pk=obj.pk).update(**{field: MADE})


@pytest.fixture
def site(user_factory, product_factory, product_image_factory, schematic_factory):
    """An imported, reviewed product on the exporting site."""
    importer, reviewer = user_factory(username='importer'), user_factory(username='reviewer', is_moderator=True)
    shared = Component.objects.create(manufacturer='Texas Instruments', part_number='LM358', component_type='ic')
    _old(shared)                                     # on both sites since the copy
    new = Component.objects.create(manufacturer='Murata', part_number='GRM155R71C104KA88D',
                                   component_type='capacitor', created_by=importer)
    new.cross_references.add(shared)
    product = product_factory(manufacturer='Asus', model_number='ET2311I', category='desktop',
                              subcategory='All-in-One', category_locked=True, is_approved=True,
                              import_source='norway-fw:ASUS_ET2311I', created_by=importer)
    image = product_image_factory(product=product, uploaded_by=importer, is_approved=True, is_primary=True)
    schematic_factory(product=product, uploaded_by=importer, is_approved=False)
    ProductComponent.objects.create(product=product, component=new, reference_designator='C1', created_by=importer)
    ProductComponent.objects.create(product=product, component=shared, reference_designator='U1')
    sheet = ComponentDatasheet.objects.create(component=new, title='GRM155', uploaded_by=importer,
                                              file=SimpleUploadedFile('grm.pdf', b'%PDF-1.4 test'))
    ImportReview.objects.create(batch='image-search', item_type='image', object_id=str(image.pk),
                                verdict='correct', reviewer=reviewer)
    for obj in (new, product, image, sheet):
        _made(obj)
    # ids kept apart: Django clears a deleted object's pk
    return {'product': product, 'product_pk': product.pk, 'new': new, 'new_pk': new.pk, 'shared': shared, 'sheet': sheet}


def _export(tmp_path):
    call_command('export_content', str(tmp_path), '--since', SINCE, '--no-md5')
    return tmp_path


def _as_other_site(site):
    """The other site: none of the exported rows, but its own copy of the shared part."""
    product = site['product']
    ProductComponent.objects.filter(product=product).delete()
    ImportReview.objects.all().delete()
    ProductImage.objects.filter(product=product).delete()
    Schematic.objects.filter(product=product).delete()
    ComponentDatasheet.objects.filter(pk=site['sheet'].pk).delete()
    product.delete()
    site['new'].delete()


def test_round_trip_keeps_review_state_and_merges_clashes(site, tmp_path, user_factory):
    out = _export(tmp_path)
    _as_other_site(site)
    # the other site made the same capacitor itself after the copy
    theirs = Component.objects.create(manufacturer='Murata', part_number='GRM155R71C104KA88D', component_type='capacitor')

    call_command('load_content', str(out))

    product = Product.objects.get(pk=site['product_pk'])
    assert (product.category, product.subcategory, product.category_locked, product.is_approved) == \
        ('desktop', 'All-in-One', True, True)
    assert product.created_by.username == 'importer'
    assert product.images.get().is_approved and not product.schematics.get().is_approved
    assert not Component.objects.filter(pk=site['new_pk']).exists()           # merged into theirs
    assert set(product.product_components.values_list('component__pk', flat=True)) == {theirs.pk, site['shared'].pk}
    assert ComponentDatasheet.objects.get(component=theirs).title == 'GRM155'
    assert list(theirs.cross_references.all()) == [site['shared']]
    theirs.refresh_from_db()
    assert theirs.usage_count == 1
    assert ImportReview.objects.get().reviewer.username == 'reviewer'
    assert Product.objects.filter(pk=product.pk, search_vector__isnull=False).exists()
    # dates come from the exporting site, not the load
    assert abs(product.created_at - MADE) < datetime.timedelta(seconds=1)
    assert abs(product.images.get().uploaded_at - MADE) < datetime.timedelta(seconds=1)
    assert abs(ComponentDatasheet.objects.get(component=theirs).uploaded_at - MADE) < datetime.timedelta(seconds=1)
    assert theirs.created_at > MADE + datetime.timedelta(hours=1)            # theirs keeps its own

    call_command('load_content', str(out))                                  # a second run adds nothing
    assert ProductComponent.objects.filter(product=product).count() == 2
    assert ComponentDatasheet.objects.filter(component=theirs).count() == 1


def test_product_the_other_site_already_has_gets_the_files(site, tmp_path, product_factory):
    out = _export(tmp_path)
    _as_other_site(site)
    theirs = product_factory(manufacturer='Asus', model_number='ET2311I', category='laptop', is_approved=True)

    call_command('load_content', str(out))

    theirs.refresh_from_db()
    assert theirs.category == 'laptop'                                        # their row is kept
    assert theirs.images.count() == 1 and theirs.product_components.count() == 2
    assert theirs.component_count == 2


def test_dry_run_and_missing_media(site, tmp_path):
    out = _export(tmp_path)
    _as_other_site(site)
    call_command('load_content', str(out), '--dry-run')
    assert not Product.objects.filter(import_source__startswith='norway').exists()

    with open(os.path.join(out, 'files.tsv'), 'a') as fh:
        fh.write('datasheets/not-copied.pdf\t10\t\n')
    with pytest.raises(CommandError, match='copy the media files first'):
        call_command('load_content', str(out))


def test_restore_dates_repairs_an_earlier_load(site, tmp_path):
    """A site loaded before dates were kept: put them back, but leave rows edited since then."""
    out = _export(tmp_path)
    _as_other_site(site)
    call_command('load_content', str(out))
    now = timezone.now() + datetime.timedelta(hours=2)                       # stamped by a later load
    Product.objects.filter(pk=site['product_pk']).update(created_at=now, updated_at=now)
    ProductImage.objects.update(uploaded_at=now)
    ProductComponent.objects.update(created_at=now, updated_at=now + datetime.timedelta(hours=1))   # edited here

    call_command('load_content', str(out), '--restore-dates')

    product = Product.objects.get(pk=site['product_pk'])
    assert abs(product.created_at - MADE) < datetime.timedelta(seconds=1)
    assert product.updated_at < now
    assert ProductImage.objects.get().uploaded_at < now
    placement = ProductComponent.objects.filter(product=product).first()
    assert placement.created_at < now and placement.updated_at == now + datetime.timedelta(hours=1)
    assert Product.objects.count() == 1                                      # nothing else loaded
