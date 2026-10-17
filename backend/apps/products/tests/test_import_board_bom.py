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
    refs = [f'C{i}' for i in range(1, 200)]
    chunks = list(refdes_chunks(refs, limit=255))
    assert [r for c in chunks for r in c] == refs
    assert all(len(', '.join(c)) <= 255 for c in chunks)


def test_import_creates_unapproved_product_components_and_cross_refs(tmp_path, user_factory):
    user_factory(is_superuser=True, is_staff=True)
    _run(_write(tmp_path, _bundle()))

    product = Product.objects.get(manufacturer='ASUS', model_number='P4SD-VX', revision='R2.01')
    assert not product.is_approved
    assert product.category == 'desktop' and product.subcategory == 'Motherboard'
    assert 'norway-bom:Asus_P4SD-VX_R2.01' in product.teardown_notes

    opamp = Component.objects.get(manufacturer='Texas Instruments', part_number='LM358DR')
    assert opamp.cross_references.filter(part_number='LM358MX').exists()
    generic = Component.objects.get(manufacturer='Generic', part_number='RES 10K 1% 1/10W 0603')
    assert generic.specifications['resistance_ohm'] == 10000.0
    yageo = Component.objects.get(manufacturer='YAGEO', part_number='RC0603FR-0710KL')
    assert generic.cross_references.filter(pk=yageo.pk).exists()
    assert yageo.cross_references.filter(pk=generic.pk).exists()      # symmetrical

    placements = ProductComponent.objects.filter(product=product, component=generic)
    assert sum(p.quantity for p in placements) == 80                   # split across rows
    assert all(len(p.reference_designator) <= 255 for p in placements)
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
