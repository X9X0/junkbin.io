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
    assert 'links added 2' in out
    assert {l.host_id for l in ProductLink.objects.filter(part=board)} == {pc.pk, other.pk}
    assert 'links kept 2' in _run(tmp_path, facts)


def test_facts_write_description_and_links_idempotently(tmp_path):
    laptop = Product.objects.create(manufacturer='Lenovo', model_number='G50-70', category='laptop',
                                    description='Lenovo G50-70 laptop.', import_source='norway-fw:x')
    b1 = Product.objects.create(manufacturer='Lenovo', model_number='NM-A271', revision='1.0', category='laptop',
                                import_source='norway-board:Lenovo_NM-A271_1.0')
    b2 = Product.objects.create(manufacturer='Lenovo', model_number='NM-A271', revision='0.1', category='laptop',
                                import_source='norway-board:Lenovo_NM-A271_0.1')
    facts = [{'product_id': str(laptop.pk), 'boards': [{'maker': 'Lenovo', 'code': 'NM-A271', 'n': 5},
                                                        {'maker': 'Compal', 'code': 'LA-9999P', 'n': 2}],
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
