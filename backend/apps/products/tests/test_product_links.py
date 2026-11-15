"""Board-to-device links: a bundle names the devices a board is fitted in; names that are exactly a
product on the site become ProductLink rows (unapproved, in review batch norway-board-links); the
product API shows approved links both ways; export/load carry them to the other site."""
import json
from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.products import import_review
from apps.products.management.commands.import_board_bom import Command
from apps.products.models import Product, ProductLink

pytestmark = pytest.mark.django_db


def _board_bundle(links):
    return {
        'bundle_version': 1, 'source_tag': 'norway-board:Compal_LA-D993P_1.0',
        'source_note': 'Schematics from the letus.repair collection, filed by the board code.',
        'product': {'manufacturer': 'Compal', 'model_number': 'LA-D993P', 'revision': '1.0', 'category': 'laptop',
                    'subcategory': 'Mainboard', 'year_manufactured': 2016,
                    'description': 'Compal LA-D993P notebook mainboard. Used in: Dell Inspiron 15 Gaming 7567.'},
        'components': [], 'documents': [], 'links': links,
    }


def _write(tmp_path, bundle, name='Compal_LA-D993P_1.0'):
    folder = tmp_path / name
    folder.mkdir()
    (folder / 'bundle.json').write_text(json.dumps(bundle))
    return folder


def _run(*args):
    out = StringIO()
    call_command('import_board_bom', *map(str, args), stdout=out)
    return out.getvalue()


@pytest.fixture
def hosts():
    return [
        Product.objects.create(manufacturer='Dell', model_number='Inspiron 15 7567', category='laptop', is_approved=True),
        Product.objects.create(manufacturer='Dell', model_number='Inspiron 7567', revision='A00', category='laptop',
                               is_approved=True),
        Product.objects.create(manufacturer='Lenovo', model_number='ThinkPad T440', category='laptop', is_approved=True),
        Product.objects.create(manufacturer='Lenovo', model_number='T440', category='laptop', is_approved=False),
        Product.objects.create(manufacturer='Acer', model_number='Aspire E1-471', category='laptop', is_approved=True),
        Product.objects.create(manufacturer='HP', model_number='ProBook 450 G4', category='laptop', is_approved=True),
    ]


def test_host_products_match_exactly_not_by_substring(hosts):
    names = lambda ps: sorted(f'{p.manufacturer} {p.model_number}' for p in ps)
    assert names(Command.host_products('Dell Inspiron 15 7567')) == ['Dell Inspiron 15 7567']
    assert names(Command.host_products('Dell Inspiron 7567')) == ['Dell Inspiron 7567']
    # with or without the family word; every revision of the model
    assert names(Command.host_products('Lenovo ThinkPad T440')) == ['Lenovo T440', 'Lenovo ThinkPad T440']
    # a multi-model name links each model
    assert names(Command.host_products('Acer Aspire E1-431 E1-471')) == ['Acer Aspire E1-471']
    # 'HP G4' must not reach ProBook 450 G4; a family word alone names nothing
    assert Command.host_products('HP G4') == []
    assert Command.host_products('HP Pavilion') == []
    assert Command.host_products('Dell') == []


def test_import_creates_tagged_links_and_syncs_them(tmp_path, hosts):
    folder = _write(tmp_path, _board_bundle([
        {'host': 'Dell Inspiron 15 7567', 'kind': 'fitted_in', 'evidence': 'named in the filename'},
        {'host': 'Lenovo ThinkPad T440', 'kind': 'fitted_in', 'evidence': 'parts listing'},
        {'host': 'Sony Vaio SVF15N', 'kind': 'fitted_in', 'evidence': 'no such product here'},
    ]))
    out = _run(folder)
    assert 'links added 3' in out and 'links unresolved 1' in out
    board = Product.objects.get(model_number='LA-D993P')
    links = ProductLink.objects.filter(part=board)
    assert links.count() == 3 and not links.filter(is_approved=True).exists()
    assert set(links.values_list('import_source', flat=True)) == {'norway-board-links:Compal_LA-D993P_1.0'}
    assert links.get(host__model_number='Inspiron 15 7567').evidence == 'named in the filename'
    # re-import with one device dropped: its link goes, the others stay (idempotent)
    folder2 = _write(tmp_path / 'again', _board_bundle([
        {'host': 'Dell Inspiron 15 7567', 'kind': 'fitted_in', 'evidence': 'named in the filename and a parts listing'},
    ])) if (tmp_path / 'again').mkdir() is None else None
    out = _run(folder2)
    assert 'links kept 1' in out and 'links removed 2' in out
    assert ProductLink.objects.filter(part=board).count() == 1
    assert ProductLink.objects.get(part=board).evidence == 'named in the filename and a parts listing'
    # dry run writes nothing
    out = _run(folder, '--dry-run')
    assert 'links added 2' in out and ProductLink.objects.filter(part=board).count() == 1


def test_review_batch_and_approval(tmp_path, hosts):
    _run(_write(tmp_path, _board_bundle([{'host': 'Dell Inspiron 15 7567', 'kind': 'fitted_in', 'evidence': 'e'}])))
    s = import_review.stats('norway-board-links')
    assert s['total'] == 1 and s['unapproved'] == 1 and s['item_type'] == 'link'
    link = import_review.items('norway-board-links').get()
    ev = import_review.evidence('norway-board-links', link)
    assert ev['item_type'] == 'link' and 'LA-D993P fitted in Dell Inspiron 15 7567' in ev['title']
    assert [d['type'] for d in ev['documents']] == ['Board', 'Fitted in']
    counts = import_review.approve_batch('norway-board-links', force=True)
    assert counts['links'] == 1 and ProductLink.objects.get().is_approved


def test_product_api_shows_approved_links_both_ways(tmp_path, hosts):
    _run(_write(tmp_path, _board_bundle([{'host': 'Lenovo ThinkPad T440', 'kind': 'fitted_in', 'evidence': 'e'}])))
    board = Product.objects.get(model_number='LA-D993P')
    board.is_approved = True
    board.save()
    client = APIClient()
    assert client.get(f'/api/products/{board.pk}/').json()['fitted_in'] == []       # unapproved links are hidden
    ProductLink.objects.update(is_approved=True)
    fitted = client.get(f'/api/products/{board.pk}/').json()['fitted_in']
    assert [f['model_number'] for f in fitted] == ['ThinkPad T440']                      # the unapproved T440 host stays hidden
    t440 = Product.objects.get(model_number='ThinkPad T440')
    parts = client.get(f'/api/products/{t440.pk}/').json()['parts']
    assert [p['model_number'] for p in parts] == ['LA-D993P'] and parts[0]['subcategory'] == 'Mainboard'


def test_links_travel_with_export_and_load(tmp_path, hosts, settings):
    _run(_write(tmp_path, _board_bundle([{'host': 'Lenovo ThinkPad T440', 'kind': 'fitted_in', 'evidence': 'e'}])))
    out = tmp_path / 'export'
    call_command('export_content', str(out), '--since', '2020-01-01', '--no-md5')
    assert (out / 'products.ProductLink.jsonl').read_text().strip()
    ProductLink.objects.all().delete()
    Product.objects.filter(model_number='LA-D993P').delete()
    call_command('load_content', str(out), '--allow-missing-files')
    links = ProductLink.objects.filter(part__model_number='LA-D993P')
    assert sorted(l.host.model_number for l in links) == ['T440', 'ThinkPad T440']      # both revisions of the host
    call_command('load_content', str(out), '--allow-missing-files')                  # loading twice adds nothing
    assert ProductLink.objects.count() == 2
