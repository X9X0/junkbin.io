"""
Tests for the import_board_bom management command.
"""
import json
from io import StringIO

import pytest
from django.core.management import call_command

from apps.components.models import Component, ProductComponent
from apps.products.management.commands.import_board_bom import refdes_chunks
from apps.products.models import Product

pytestmark = pytest.mark.django_db


def _bundle(**overrides):
    bundle = {
        'bundle_version': 1,
        'source_tag': 'norway-bom:Asus_P4SD-VX_R2.01',
        'source_note': 'Component list from the factory production BOM dated 2003-05-12.',
        'product': {
            'manufacturer': 'ASUS', 'model_number': 'P4SD-VX', 'revision': 'R2.01',
            'category': 'desktop', 'subcategory': 'Motherboard', 'year_manufactured': 2003,
            'description': 'ASUS P4SD-VX motherboard, PCB revision R2.01.',
        },
        'components': [
            {
                'part_number': 'LM358DR', 'manufacturer': 'Texas Instruments',
                'component_type': 'opamp', 'package_type': '', 'description': 'OP AMP. LM358DR S-8 TI',
                'specifications': {}, 'reference_designators': ['U12', 'U14'], 'quantity': 2,
                'notes': 'Factory BOM line: OP AMP. LM358DR S-8 TI',
                'alternates': [{'part_number': 'LM358MX', 'manufacturer': 'National Semiconductor (TI)'}],
                'equivalents': [],
            },
            {
                'part_number': 'RES 10K 1% 1/10W 0603', 'manufacturer': 'Generic',
                'component_type': 'resistor', 'package_type': '0603',
                'description': 'Generic resistor: RES 10K 1% 1/10W 0603',
                'specifications': {'resistance_ohm': 10000.0, 'tolerance': '1%', 'power_w': 0.1},
                'reference_designators': [f'R{i}' for i in range(1, 81)], 'quantity': 80,
                'notes': 'Factory BOM line: RES 10K OHM 1/10W (0603) 1%',
                'alternates': [],
                'equivalents': [{
                    'part_number': 'RC0603FR-0710KL', 'manufacturer': 'YAGEO',
                    'component_type': 'resistor', 'package_type': '0603',
                    'description': '10 kOhms ±1% 0.1W Chip Resistor 0603',
                    'specifications': {'resistance_ohm': 10000.0, 'tolerance': '1%', 'power_w': 0.1},
                }],
            },
        ],
    }
    bundle.update(overrides)
    return bundle


def _write(tmp_path, bundle, name='Asus_P4SD-VX_R2.01'):
    folder = tmp_path / name
    folder.mkdir()
    (folder / 'bundle.json').write_text(json.dumps(bundle))
    return folder


def _run(*args):
    out = StringIO()
    call_command('import_board_bom', *map(str, args), stdout=out)
    return out.getvalue()


def test_refdes_chunks_fit_the_column():
    refs = [f'C{i}' for i in range(1, 900)]
    chunks = list(refdes_chunks(refs, limit=2000))
    assert [r for c in chunks for r in c] == refs
    assert all(len(', '.join(c)) <= 2000 for c in chunks)


def test_import_creates_unapproved_product_components_and_cross_refs(tmp_path, user_factory):
    user_factory(is_superuser=True, is_staff=True)
    _run(_write(tmp_path, _bundle()))

    product = Product.objects.get(manufacturer='ASUS', model_number='P4SD-VX', revision='R2.01')
    assert not product.is_approved
    assert product.category == 'desktop' and product.subcategory == 'Motherboard'
    assert product.import_source == 'norway-bom:Asus_P4SD-VX_R2.01'
    assert product.teardown_notes == ''                                 # nothing internal on display
    assert 'factory production BOM' in product.description
    assert not ProductComponent.objects.filter(notes__startswith='[').exists()

    opamp = Component.objects.get(manufacturer='Texas Instruments', part_number='LM358DR')
    assert opamp.cross_references.filter(part_number='LM358MX').exists()
    alternate = Component.objects.get(part_number='LM358MX')                # described as an alternate,
    assert alternate.description.startswith('Factory-approved alternate to Texas Instruments LM358DR')  # not as LM358DR
    generic = Component.objects.get(manufacturer='Generic', part_number='RES 10K 1% 1/10W 0603')
    assert generic.specifications['resistance_ohm'] == 10000.0
    yageo = Component.objects.get(manufacturer='YAGEO', part_number='RC0603FR-0710KL')
    assert generic.cross_references.filter(pk=yageo.pk).exists()
    assert yageo.cross_references.filter(pk=generic.pk).exists()      # symmetrical

    placements = ProductComponent.objects.filter(product=product, component=generic)
    assert placements.count() == 1 and placements.get().quantity == 80   # one row holds all 80 positions
    assert product.component_count == ProductComponent.objects.filter(product=product).count()
    assert generic.__class__.objects.get(pk=generic.pk).usage_count == placements.count()


def test_reimport_replaces_instead_of_duplicating(tmp_path, user_factory):
    user_factory(is_superuser=True, is_staff=True)
    folder = _write(tmp_path, _bundle())
    _run(folder)
    first = ProductComponent.objects.count()
    _run(folder)
    assert Product.objects.count() == 1
    assert ProductComponent.objects.count() == first


def test_existing_product_without_tag_is_left_alone(tmp_path, user_factory, product_factory):
    user_factory(is_superuser=True, is_staff=True)
    product = product_factory(manufacturer='ASUS', model_number='P4SD-VX', revision='R2.01',
                              region='global', teardown_notes='hand-documented by a contributor')
    out = _run(_write(tmp_path, _bundle()))
    assert 'products skipped 1' in out
    assert not ProductComponent.objects.filter(product=product).exists()


def test_existing_component_is_reused_not_edited(tmp_path, user_factory, component_factory):
    user_factory(is_superuser=True, is_staff=True)
    existing = component_factory(manufacturer='Texas Instruments', part_number='LM358DR',
                                 description='Curated description')
    _run(_write(tmp_path, _bundle()))
    existing.refresh_from_db()
    assert existing.description == 'Curated description'
    assert Component.objects.filter(part_number__iexact='LM358DR').count() == 1


def test_dry_run_rolls_back(tmp_path, user_factory):
    user_factory(is_superuser=True, is_staff=True)
    out = _run(_write(tmp_path, _bundle()), '--dry-run')
    assert 'DRY RUN' in out and 'products created 1' in out
    assert not Product.objects.exists()
    assert not Component.objects.exists()


def _with_doc(tmp_path, name='Asus_P4SD-VX_R2.01', content=b'PK fake zip'):
    import hashlib
    folder = _write(tmp_path, _bundle(), name)
    (folder / 'docs').mkdir()
    (folder / 'docs' / '60-M8LA4J-C06.zip').write_bytes(content)
    bundle = json.loads((folder / 'bundle.json').read_text())
    bundle['documents'] = [{
        'file': 'docs/60-M8LA4J-C06.zip', 'md5': hashlib.md5(content).hexdigest(),
        'schematic_type': 'other', 'title': 'Factory files: 60-M8LA4J-C06 (30 files)',
        'description': 'All files from the build folder', 'source_notes': 'letus.repair collection: x/',
    }]
    (folder / 'bundle.json').write_text(json.dumps(bundle))
    return folder


def test_documents_are_attached_once_unapproved(tmp_path, settings, user_factory):
    from apps.products.models import Schematic
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    folder = _with_doc(tmp_path)
    _run(folder)
    docs = Schematic.objects.all()
    assert docs.count() == 1
    doc = docs.get()
    assert not doc.is_approved and doc.source_type == 'leaked' and doc.file_type == 'zip'
    assert doc.version == 'R2.01'
    assert 'documents kept 1' in _run(folder)
    assert Schematic.objects.count() == 1


def test_document_dropped_from_bundle_is_removed(tmp_path, settings, user_factory):
    from apps.products.models import Schematic
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    folder = _with_doc(tmp_path)
    _run(folder)
    bundle = json.loads((folder / 'bundle.json').read_text())
    bundle['documents'] = []
    (folder / 'bundle.json').write_text(json.dumps(bundle))
    _run(folder)
    assert not Schematic.objects.exists()


def test_dry_run_writes_no_documents(tmp_path, settings, user_factory):
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    out = _run(_with_doc(tmp_path), '--dry-run')
    assert 'documents added 1' in out
    assert not (tmp_path / 'media').exists() or not any((tmp_path / 'media').rglob('*.zip'))


def test_documents_only_leaves_components_alone(tmp_path, settings, user_factory):
    from apps.products.models import Schematic
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    plain = _write(tmp_path, _bundle(), 'first')
    _run(plain)
    placements = set(ProductComponent.objects.values_list('pk', flat=True))
    out = _run(_with_doc(tmp_path, name='second'), '--skip-components')
    assert 'documents added 1' in out
    assert set(ProductComponent.objects.values_list('pk', flat=True)) == placements
    assert Schematic.objects.count() == 1


def test_corrected_revision_updates_the_same_product(tmp_path, user_factory):
    user_factory(is_superuser=True, is_staff=True)
    bundle = _bundle()
    bundle['product']['revision'] = 'R1.03.(SERVER)'
    _run(_write(tmp_path, bundle, 'first'))
    product = Product.objects.get()
    bundle['product']['revision'] = '1.03 (server)'
    bundle['product']['description'] = 'Same circuit board as: ASUS X Rev 1.0 (99% of placements identical).'
    _run(_write(tmp_path, bundle, 'second'), '--skip-components')
    assert Product.objects.count() == 1
    product.refresh_from_db()
    assert product.revision == '1.03 (server)'
    assert 'Same circuit board as' in product.description
    assert 'factory production BOM' in product.description             # provenance kept on update


def test_attach_to_existing_adds_documents_only(tmp_path, settings, user_factory, product_factory):
    from apps.products.models import Schematic
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    product = product_factory(manufacturer='ASUS', model_number='P4SD-VX', revision='R2.01',
                              region='global', description='curated', teardown_notes='by a contributor')
    folder = _with_doc(tmp_path)
    bundle = json.loads((folder / 'bundle.json').read_text())
    bundle.update(components=[], attach_to_existing=True, source_tag='norway-schem:x')
    bundle['product']['description'] = 'import text'
    (folder / 'bundle.json').write_text(json.dumps(bundle))
    out = _run(folder)
    assert 'products attached 1' in out
    product.refresh_from_db()
    assert product.description == 'curated'
    assert Schematic.objects.filter(product=product).count() == 1
    assert Product.objects.count() == 1


def test_cover_image_added_once_as_preview(tmp_path, settings, user_factory):
    from io import BytesIO
    from PIL import Image
    from apps.products.models import ProductImage
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    folder = _write(tmp_path, _bundle(), 'cover')
    (folder / 'docs').mkdir()
    buf = BytesIO()
    Image.new('RGB', (40, 30), 'white').save(buf, 'JPEG')
    (folder / 'docs' / 'cover.jpg').write_bytes(buf.getvalue())
    bundle = json.loads((folder / 'bundle.json').read_text())
    bundle['images'] = [{'file': 'docs/cover.jpg', 'md5': 'x', 'caption': 'First page of the schematic: X',
                         'image_type': 'schematic'}]
    (folder / 'bundle.json').write_text(json.dumps(bundle))
    _run(folder)
    _run(folder, '--skip-components')
    img = ProductImage.objects.get()
    assert img.is_primary and not img.is_approved and img.image_type == 'schematic'


def _with_firmware(tmp_path, name='Dell_Latitude_E6530', content=b'\xffBIOS image\x00' * 64, **product):
    import hashlib
    bundle = _bundle(source_tag=f'norway-fw:{name}', attach_to_existing=True, components=[],
                     product={'manufacturer': 'Dell', 'model_number': 'Latitude E6530', 'revision': '',
                              'category': 'laptop', 'subcategory': '', 'description': 'Dell Latitude E6530.',
                              **product})
    folder = _write(tmp_path, bundle, name)
    (folder / 'firmware').mkdir()
    (folder / 'firmware' / '94001_EN25Q64.BIN').write_bytes(content)
    bundle['firmware'] = [{
        'file': 'firmware/94001_EN25Q64.BIN', 'md5': hashlib.md5(content).hexdigest(),
        'title': 'EN25Q64.BIN - Dell Latitude E6530 flash dump', 'version': '', 'chip_architecture': 'EN25Q64',
        'description': 'Flash dump filed as "Dell Latitude E6530 (LA-7762P Rev. 1.0)".',
        'source_notes': 'Unsorted/x/EN25Q64.BIN (letus.repair file 94001)',
    }]
    (folder / 'bundle.json').write_text(json.dumps(bundle))
    return folder


def test_firmware_is_stored_unmodified_unapproved_once(tmp_path, settings, user_factory):
    from apps.products.models import Firmware
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    content = b'\xffBIOS image\x00MSDM' * 64
    folder = _with_firmware(tmp_path, content=content)
    assert 'firmware added 1' in _run(folder)
    fw = Firmware.objects.get()
    assert not fw.is_approved and fw.source_type == 'dumped' and fw.chip_architecture == 'EN25Q64'
    assert fw.product.category == 'laptop' and not fw.product.is_approved
    with fw.file.open('rb') as fh:
        assert fh.read() == content                                    # byte for byte as dumped
    assert 'firmware kept 1' in _run(folder)
    assert Firmware.objects.count() == 1


def test_firmware_attaches_to_someone_elses_product(tmp_path, settings, user_factory, product_factory):
    from apps.products.models import Firmware
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    product = product_factory(manufacturer='Dell', model_number='Latitude E6530', revision='', region='global',
                              description='curated')
    out = _run(_with_firmware(tmp_path))
    assert 'products attached 1' in out
    product.refresh_from_db()
    assert product.description == 'curated'
    assert Firmware.objects.filter(product=product).count() == 1


def test_firmware_dry_run_writes_nothing(tmp_path, settings, user_factory):
    from apps.products.models import Firmware
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    out = _run(_with_firmware(tmp_path), '--dry-run')
    assert 'firmware added 1' in out
    assert Firmware.objects.count() == 0
    assert not (tmp_path / 'media').exists() or not any((tmp_path / 'media').rglob('*.BIN'))
