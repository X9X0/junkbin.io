"""stub_names: one spelling per machine, and dedupe_stub_machines folding the others into it."""
from io import StringIO

import pytest
from django.core.management import call_command

from apps.products.models import Product, ProductLink
from apps.products.stub_names import Resolver, families_compatible, model_keys

pytestmark = pytest.mark.django_db

STUB = 'norway-machine:test'


def product(brand, model, src='norway-fw:test', category='laptop', approved=False):
    return Product.objects.create(manufacturer=brand, model_number=model, category=category, import_source=src,
                                  is_approved=approved, description='x')


def test_model_keys_ignore_dashes_spaces_and_a_leading_screen_size():
    assert model_keys(['15-3567'])[0] == '3567'
    assert model_keys(['15', '3567'])[0] == '3567'
    assert model_keys(['3567'])[0] == '3567'
    assert model_keys(['15-3567'])[1] == '153567'           # the strict key keeps the size
    assert model_keys(['15-3567'])[2] == '15'
    assert model_keys(['13-2000'])[2] == '13'
    assert model_keys(['M11X', 'R3'])[0] == 'M11XR3'


def test_families_compatible():
    assert families_compatible(set(), {'inspiron'})
    assert families_compatible({'inspiron'}, {'inspiron', 'gaming'})
    assert not families_compatible({'vostro'}, {'latitude'})
    assert not families_compatible({'thinkpad'}, {'thinkpad', 'yoga'})       # L390 / L390 Yoga: different machines
    assert families_compatible(set(), {'yoga'})                             # a bare name is only underspecified


def test_clean_fixes_typos_against_the_brands_own_words():
    for m in ('Inspiron 3567', 'Inspiron 5567', 'Latitude E6430', 'Latitude E6440'):
        product('Dell', m)
    r = Resolver()
    assert r.clean('Dell', 'Inspirion 15-3567').name == 'Inspiron 15-3567'
    assert r.clean('Dell', 'Lattitude E5270').name == 'Latitude E5270'
    assert r.clean('Dell', 'Dell Inc. Vostro 14-5480').name == 'Vostro 14-5480'    # brand and junk dropped, Vostro unknown but kept
    assert r.clean('Huawei', 'Magicbook Pro 2020').name == 'Magicbook Pro 2020'    # never corrected to another brand's word
    assert r.clean('Lenovo', 'Flex 5-14ARE05. LC55-14A').name == 'Flex 5-14ARE05'
    assert r.clean('Lenovo', 'IdeaPad Gamming 15IAH7').name == 'IdeaPad 15IAH7'
    assert r.clean('Lenovo', 'ThinkPad X1 Carbon').family == ('ThinkPad', 'Carbon')
    assert r.clean('Lenovo', 'ThinkPad X1 Carbon').name == 'ThinkPad X1 Carbon'
    assert r.clean('HP', 'Asus M2NC51-AR') is None                                  # another maker's board
    assert r.clean('HP', 'Pavilion Slimline Asus M2NC51-AR') is None
    assert r.clean('Dell', 'Inspiron 15 3567').size == '15'
    assert r.clean('HP', '650 G1').gen == 'G1'
    assert r.clean('HP', 'Pavilion x2 12-b').name == 'Pavilion x2 12-b'                # a model's own casing is kept


def test_find_prefers_a_real_product_with_a_compatible_family():
    real = product('Dell', '15-3567')
    product('Dell', 'Latitude 5590')
    product('Dell', 'Vostro 3445')
    r = Resolver()
    assert r.find('Dell', 'Inspirion 15-3567') == real
    assert r.find('Dell', 'Inspiron 3567') is None               # a family word on one side only: the sizes must agree too
    assert r.find('Dell', 'Inspiron 15 3567') == real
    assert r.find('Dell', 'Vostro 5590') is None                 # shares the number, not the family
    assert r.find('Dell', '3445') == Product.objects.get(model_number='Vostro 3445')


def test_find_leaves_ambiguous_and_series_names_alone():
    product('Dell', 'Vostro 5510')
    product('Dell', 'Precision 5510')
    product('Dell', 'Inspiron 14 5000')
    product('HP', '2000')
    product('HP', 'Mini Note DM 1000')
    r = Resolver()
    assert r.find('Dell', '5510') is None                        # two families exclude each other
    assert r.find('Dell', 'Inspiron 15-5000') is None            # a series under another size
    assert r.find('Dell', 'Inspiron 5000') is None
    assert r.find('Dell', 'Inspiron 14-5000') is not None
    assert r.find('HP', 'Spectre XT 13-2000') is None            # not the HP 2000
    assert r.find('HP', '1000') is None                          # not the Mini Note DM 1000


def test_find_phone_numbers_need_the_exact_family():
    product('Apple', 'iPad Pro 1', src=STUB, category='tablet')
    product('Apple', 'iPad Air 2', src=STUB, category='tablet')
    r = Resolver()
    assert r.find('Apple', 'iPad 1') is None
    assert r.find('Apple', 'iPad 2') is None
    assert r.find('Apple', 'iPad Air 2') is not None


def test_dedupe_merges_stubs_into_the_product_and_into_the_widest_stub():
    real = product('Dell', '15-3567', approved=True)
    board = product('Compal', 'LA-D821P', src='norway-board:Compal_LA-D821P_1.0')
    board2 = product('Compal', 'LA-D822P', src='norway-board:Compal_LA-D822P_1.0')
    typo = product('Dell', 'Inspirion 15-3567', src=STUB)
    gaming = product('Dell', 'Inspiron Gaming 15-3567', src=STUB)
    ProductLink.objects.create(part=board, host=typo, kind='fitted_in', import_source='t', is_approved=True)
    ProductLink.objects.create(part=board, host=real, kind='fitted_in', import_source='t')          # twin: dropped
    ProductLink.objects.create(part=board2, host=gaming, kind='fitted_in', import_source='t')        # moved
    wide = product('Lenovo', 'IdeaPad Flex 5-14ARE05', src=STUB)
    product('Lenovo', 'IdeaPad 5-14ARE05', src=STUB)
    product('Lenovo', 'Flex 5-14ARE05. LC55-14A', src=STUB)
    product('Lenovo', 'ThinkPad L390', src=STUB)
    product('Lenovo', 'ThinkPad L390 Yoga', src=STUB)
    product('HP', 'Asus M2NC51-AR', src=STUB)
    for m in ('Inspiron 5567', 'Inspiron 7567'):
        product('Dell', m)
    out = StringIO()
    call_command('dedupe_stub_machines', stdout=out)
    assert not Product.objects.filter(pk__in=[typo.pk, gaming.pk]).exists()
    assert Product.objects.filter(manufacturer='Lenovo', import_source=STUB).count() == 3       # Flex survivor + L390 + L390 Yoga
    assert Product.objects.filter(manufacturer='Lenovo', model_number='IdeaPad Flex 5-14ARE05').exists()
    assert not Product.objects.filter(manufacturer='HP', model_number='Asus M2NC51-AR').exists()
    links = ProductLink.objects.filter(host=real)
    assert links.count() == 2
    assert links.get(part=board).is_approved                      # approval of the dropped twin kept
    assert links.filter(part=board2).exists()
    assert 'merged into product 2' in out.getvalue()
    assert 'merged into stub 2' in out.getvalue()
    assert 'deleted (no machine model) 1' in out.getvalue()
    out = StringIO()
    call_command('dedupe_stub_machines', stdout=out)              # a second run changes nothing
    assert 'merged' not in out.getvalue().replace('merged into product 0', '').replace('merged into stub 0', '')
    assert wide.pk == Product.objects.get(model_number='IdeaPad Flex 5-14ARE05').pk


def test_dedupe_renames_a_stub_to_its_cleaned_form_and_keeps_case_only_differences():
    product('Dell', 'Inspiron 3567')
    product('Dell', 'Inspiron 5567')
    s = product('Dell', 'Dell Inspirion 17-7778', src=STUB)
    legion = product('Lenovo', 'LEGION Y520', src=STUB)
    call_command('dedupe_stub_machines', stdout=StringIO())
    s.refresh_from_db()
    legion.refresh_from_db()
    assert s.model_number == 'Inspiron 17-7778'
    assert legion.model_number == 'LEGION Y520'


def test_dedupe_approved_stub_makes_its_survivor_approved():
    survivor = product('Toshiba', 'Satellite P750', src=STUB)
    product('Toshiba', 'Satellite L500')
    product('Toshiba', 'Satellite L505')
    product('Toshiba', 'Staellite P750', src=STUB, approved=True)
    call_command('dedupe_stub_machines', stdout=StringIO())
    survivor.refresh_from_db()
    assert survivor.is_approved
    assert Product.objects.filter(manufacturer='Toshiba', import_source=STUB).count() == 1


def test_find_takes_the_product_spelled_as_the_name_when_several_real_ones_share_its_family():
    product('Lenovo', 'Yoga 11S')
    product('Lenovo', 'Yoga 11S VIUU4')
    product('Lenovo', 'ALL IN ONE C240', category='desktop')
    product('Lenovo', 'C240', src=STUB)
    r = Resolver()
    assert r.find('Lenovo', 'IdeaPad Yoga 11S') == Product.objects.get(model_number='Yoga 11S')
    assert r.clean('Lenovo', 'ALL IN ONE C240').family == ()                          # a form factor, not a family
    assert r.find('Lenovo', 'Lenovo Aio C240') == Product.objects.get(model_number='ALL IN ONE C240')


def test_make_stub_never_creates_a_name_the_site_has():
    from apps.products.management.commands.import_board_bom import Command as Importer
    product('Lenovo', 'IdeaPad 320')
    product('Lenovo', 'IdeaPad 330')
    product('Lenovo', 'IdeaPad Yoga 11S', src=STUB)
    product('Lenovo', 'Yoga 11S')
    product('Lenovo', 'Yoga 11S VIUU4')
    product('Lenovo', 'Yoga 11S 20246', category='tablet')                          # three real ones: ambiguous
    Importer._resolver = None
    got = Importer.make_stub('Lenovo Ideadpad Yoga 11S', 'laptop', tag=STUB, describe=lambda b, m: 'x', user=None,
                             dry_run=False, result={})
    assert got == Product.objects.get(model_number='Yoga 11S')                         # the real one, spelled plainly
    assert Product.objects.filter(model_number='IdeaPad Yoga 11S').count() == 1       # and nothing new beside the old stub
