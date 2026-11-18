"""import_product_facts: facts about a machine (boards inside, order numbers) land in its description
and become board -> machine links to board products on the site."""
import json
from io import StringIO

import pytest
from django.core.management import call_command

from apps.products.management.commands.import_product_facts import facts_sentence
from apps.products.models import Product, ProductLink

pytestmark = pytest.mark.django_db


def _run(tmp_path, facts, *args):
    path = tmp_path / 'facts.json'
    path.write_text(json.dumps(facts))
    out = StringIO()
    call_command('import_product_facts', str(path), *args, stdout=out)
    return out.getvalue()


def test_sentence():
    assert facts_sentence([{'maker': 'Lenovo', 'code': 'NM-A271', 'n': 3}], ['Lenovo FRU 5B20G36639']) == \
        ' Boards inside: Lenovo NM-A271. Mainboard sold as Lenovo FRU 5B20G36639 (web search).'
    assert facts_sentence([], ['HP spare 1']) == ' Sold as HP spare 1 (web search).'
    assert facts_sentence([], ['HP spare 5188-1234'], ['HP Pavilion a1250n']) == \
        ' Used in: HP Pavilion a1250n. Sold as HP spare 5188-1234 (web search).'
    assert facts_sentence([], []) == ''
    assert facts_sentence([{'maker': 'Compal', 'code': 'LA-7782P', 'n': 1}], [], source='firmware label') == \
        ' Boards inside: Compal LA-7782P (firmware label).'
    assert facts_sentence([], [], notes=['OEM board for HP (HP name Leonite)', 'Intel 945P chipset, socket LGA 775, micro-ATX']) == \
        ' OEM board for HP (HP name Leonite). Intel 945P chipset, socket LGA 775, micro-ATX (web search).'


def test_board_facts_link_the_board_to_named_machines(tmp_path):
    board = Product.objects.create(manufacturer='Asus', model_number='P5LP-LE', revision='1.04', category='desktop',
                                   description='Asus P5LP-LE motherboard.', import_source='norway-schem:x')
    pc = Product.objects.create(manufacturer='HP', model_number='Pavilion a1250n', category='desktop')
    other = Product.objects.create(manufacturer='HP', model_number='Pavilion a1250n', revision='B', category='desktop')
    facts = [{'product_id': str(board.pk), 'used_in': ['HP Pavilion a1250n', 'HP Media Center m7000'],
              'parts': ['HP spare 5188-1234'], 'notes': ['OEM board for HP (HP name Leonite)', 'Intel 945P chipset, micro-ATX'],
              'evidence': 'named for the board in 7 parts listings'}]
    out = _run(tmp_path, facts)
    board.refresh_from_db()
    assert board.description == ('Asus P5LP-LE motherboard. OEM board for HP (HP name Leonite). Intel 945P chipset, micro-ATX. '
                                 'Used in: HP Pavilion a1250n, HP Media Center m7000. Sold as HP spare 5188-1234 (web search).')
    facts[0]['notes'] = ['Intel 945P chipset, micro-ATX']
    _run(tmp_path, facts)
    board.refresh_from_db()
    assert board.description.count('(web search)') == 1 and 'Leonite' not in board.description
    assert 'links added 3' in out and 'machines created 1' in out                        # HP Media Center m7000 became a stub
    m7000 = Product.objects.get(model_number='Media Center m7000')
    assert {l.host_id for l in ProductLink.objects.filter(part=board)} == {pc.pk, other.pk, m7000.pk}
    assert 'links kept 3' in _run(tmp_path, facts)


def test_facts_write_description_and_links_idempotently(tmp_path):
    laptop = Product.objects.create(manufacturer='Lenovo', model_number='G50-70', category='laptop',
                                    description='Lenovo G50-70 laptop.', import_source='norway-fw:x')
    b1 = Product.objects.create(manufacturer='Lenovo', model_number='NM-A271', revision='1.0', category='laptop',
                                import_source='norway-board:Lenovo_NM-A271_1.0')
    b2 = Product.objects.create(manufacturer='Lenovo', model_number='NM-A271', revision='0.1', category='laptop',
                                import_source='norway-board:Lenovo_NM-A271_0.1')
    facts = [{'product_id': str(laptop.pk), 'boards': [{'maker': 'Lenovo', 'code': 'NM-A271', 'n': 5},
                                                        {'maker': 'Compal', 'code': 'LA-9999P', 'n': 1}],   # one listing: no stub board
              'parts': ['Lenovo FRU 5B20G36639'], 'evidence': 'named with the Lenovo G50-70 in 9 parts listings'},
             {'product_id': '00000000-0000-0000-0000-000000000000', 'boards': [], 'parts': []}]
    out = _run(tmp_path, facts, '--dry-run')
    assert 'links added 2' in out and 'codes without product 1' in out and 'missing 1' in out
    assert ProductLink.objects.count() == 0 and Product.objects.get(pk=laptop.pk).description == 'Lenovo G50-70 laptop.'
    out = _run(tmp_path, facts)
    laptop.refresh_from_db()
    assert laptop.description == ('Lenovo G50-70 laptop. Boards inside: Lenovo NM-A271, Compal LA-9999P. '
                                  'Mainboard sold as Lenovo FRU 5B20G36639 (web search).')
    links = ProductLink.objects.filter(host=laptop)
    assert {l.part_id for l in links} == {b1.pk, b2.pk} and not links.filter(is_approved=True).exists()
    assert links.first().import_source == f'norway-board-links:web:{laptop.pk}'
    assert 'is named with the Lenovo G50-70 in 9 parts listings.' in links.first().evidence
    # again, with the second revision gone from the facts' reach: the sentence is replaced, not appended
    facts[0]['boards'] = [{'maker': 'Lenovo', 'code': 'NM-A271', 'n': 5}]
    facts[0]['parts'] = []
    b2.delete()
    out = _run(tmp_path, facts)
    laptop.refresh_from_db()
    assert laptop.description == 'Lenovo G50-70 laptop. Boards inside: Lenovo NM-A271 (web search).'
    assert 'links kept 1' in out and ProductLink.objects.filter(host=laptop).count() == 1


def test_facts_fall_back_to_the_product_name_when_the_id_is_gone(tmp_path):
    board = Product.objects.create(manufacturer='Gigabyte', model_number='GA-B150M-D3V', revision='1.0', category='desktop',
                                   description='Gigabyte GA-B150M-D3V motherboard.', import_source='norway-schem:x')
    facts = [{'product_id': '00000000-0000-0000-0000-000000000001',
              'product': {'manufacturer': 'gigabyte', 'model_number': 'ga-b150m-d3v', 'revision': '1.0'},
              'notes': ['Intel B150 chipset, socket LGA 1151, micro-ATX']},
             {'product_id': '00000000-0000-0000-0000-000000000002',
              'product': {'manufacturer': 'Gigabyte', 'model_number': 'GA-B150M-D3V', 'revision': '2.0'}, 'notes': ['x']}]
    out = _run(tmp_path, facts)
    assert 'products 1' in out and 'by name 1' in out and 'missing 1' in out
    board.refresh_from_db()
    assert board.description == 'Gigabyte GA-B150M-D3V motherboard. Intel B150 chipset, socket LGA 1151, micro-ATX (web search).'


def test_board_codes_without_a_product_become_stub_boards_and_retire_when_the_real_board_arrives(tmp_path):
    laptop = Product.objects.create(manufacturer='HP', model_number='Pavilion x2 12-b', category='laptop', description='HP laptop.')
    facts = [{'product_id': str(laptop.pk), 'boards': [{'maker': 'Quanta', 'code': 'DAYB3BMBAD0', 'n': 7},
                                                        {'maker': 'Compal', 'code': 'LA-0001P', 'n': 1},
                                                        {'maker': 'Asus P/N', 'code': '69N0ABCD', 'n': 5}],
              'parts': [], 'evidence': 'named with the HP Pavilion x2 12-b in 9 parts listings found by web search'}]
    out = _run(tmp_path, facts, '--dry-run')
    assert 'board stubs created 1' in out and 'codes without product 2' in out and not Product.objects.filter(model_number='DAYB3BMBAD0').exists()
    out = _run(tmp_path, facts)
    stub = Product.objects.get(model_number='DAYB3BMBAD0')
    assert stub.manufacturer == 'Quanta' and stub.subcategory == 'Mainboard' and stub.import_source == 'norway-board-stub:Quanta_DAYB3BMBAD0'
    assert '7 parts listings' in stub.description and not stub.is_approved and 'links added 1' in out
    assert ProductLink.objects.get(host=laptop).part == stub
    assert 'board stubs created 0' in _run(tmp_path, facts)                           # idempotent
    # the schematic lane brings the real board: the stub retires and the laptop links to the real one
    real = Product.objects.create(manufacturer='Quanta', model_number='DAYB3BMBAD0', revision='1A', category='laptop',
                                  import_source='norway-board:Quanta_DAYB3BMBAD0_1A')
    out = _run(tmp_path, facts)
    assert 'board stubs retired 1' in out and not Product.objects.filter(pk=stub.pk).exists()
    assert [l.part for l in ProductLink.objects.filter(host=laptop)] == [real]
    # a BIOS label is strong enough on its own
    facts = [{'product_id': str(laptop.pk), 'boards': [{'maker': 'Compal', 'code': 'LA-0002P', 'n': 1}], 'parts': [], 'source': 'firmware label',
              'evidence': 'named on the BIOS dump label of the HP Pavilion x2 12-b'}]
    _run(tmp_path, facts)
    assert 'BIOS dump label' in Product.objects.get(model_number='LA-0002P').description


def test_machines_a_board_is_named_for_become_stubs_when_listings_are_two_or_more(tmp_path):
    Product.objects.create(manufacturer='Sony', model_number='Vaio PCV-RX550', category='desktop')          # the brand exists
    board = Product.objects.create(manufacturer='Asus', model_number='A7S-LE', revision='1.01', category='desktop',
                                   description='Asus A7S-LE motherboard.', import_source='norway-schem:x')
    facts = [{'product_id': str(board.pk), 'used_in': ['Sony Vaio PCV-RX450', 'Packard Bell iMedia 1234'], 'parts': [], 'notes': [],
              'evidence': 'named for the Asus A7S-LE in 2 parts listings found by web search'}]
    out = _run(tmp_path, facts)
    assert 'machines created 1' in out and 'links added 1' in out                        # no Packard Bell on the site
    stub = Product.objects.get(model_number='Vaio PCV-RX450')
    assert stub.manufacturer == 'Sony' and stub.category == 'desktop' and stub.import_source == f'norway-machine:facts:{board.pk}'
    assert ProductLink.objects.get(part=board).host == stub
    facts[0]['evidence'] = 'named for the Asus A7S-LE in 1 parts listings found by web search'
    facts[0]['used_in'] = ['Sony Vaio PCV-RX460']
    assert 'machines created 0' in _run(tmp_path, facts)                                # one listing is not enough


def test_a_bare_note_is_written_once_however_often_the_facts_run(tmp_path):
    board = Product.objects.create(manufacturer='MSI', model_number='MS-6758', category='desktop', import_source='norway-schem:x',
                                   description='MSI MS-6758 mainboard. ATX (web search). ATX (web search). ATX (web search).')
    facts = [{'product_id': str(board.pk), 'boards': [], 'parts': [], 'notes': ['ATX'], 'evidence': 'spec page'}]
    _run(tmp_path, facts)
    board.refresh_from_db()
    assert board.description == 'MSI MS-6758 mainboard. ATX (web search).'
    out = _run(tmp_path, facts)
    board.refresh_from_db()
    assert board.description == 'MSI MS-6758 mainboard. ATX (web search).'
    assert 'descriptions changed 0' in out
