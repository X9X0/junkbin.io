"""fix_family_typos: a typo'd family word in an imported machine name corrected to the brand's own spelling."""
from io import StringIO

import pytest
from django.core.management import call_command

from apps.products.management.commands.fix_family_typos import corrected
from apps.products.models import Firmware, Product, ProductImage, ProductLink
from apps.products.stub_names import Resolver

pytestmark = pytest.mark.django_db


def product(brand, model, src='norway-fw:test', category='laptop', approved=False, description=''):
    return Product.objects.create(manufacturer=brand, model_number=model, category=category, import_source=src,
                                  is_approved=approved, description=description or f'{brand} {model}. Firmware.')


def test_corrected_touches_family_words_before_a_model_token_only():
    for m in ('Latitude E6430', 'Latitude E6440', 'Inspiron 3567', 'Inspiron 5567', 'Medalist A', 'Medalist B'):
        product('Dell', m)
    r = Resolver()
    assert corrected(r, 'Dell', 'Latitdue E5550') == 'Latitude E5550'
    assert corrected(r, 'Dell', 'Inspirion 15-3567 (Gaming)') == 'Inspiron 15-3567 (Gaming)'
    assert corrected(r, 'Dell', 'Latitude E5550') is None                    # nothing to fix
    assert corrected(r, 'Dell', 'LATITUDE E5550') is None                    # a change of case alone is not a typo
    assert corrected(r, 'Dell', 'Lattitude') is None                         # no model token: not a machine name
    assert corrected(r, 'Dell', 'Duo-Medalist 1') is None                    # the word contains the vocab word: a variant, not a typo
    assert corrected(r, 'Dell', 'Inspiron Latitdue 3567') == 'Inspiron Latitude 3567'
    assert corrected(r, 'Dell', 'Dell Latitude E5550') == 'Latitude E5550'       # the brand repeated
    assert corrected(r, 'Dell', 'Dlel Latitude E5550') == 'Latitude E5550'       # the brand's letters rearranged
    assert corrected(r, 'Dell', 'Protage E5550') is None                         # a looser miss needs a common word


def test_a_looser_miss_counts_only_against_a_common_family_word():
    for i in range(10):
        product('Toshiba', f'Portege R{700 + i}')
    product('Toshiba', 'Tecra A10')
    product('Toshiba', 'Tecra A11')
    r = Resolver()
    assert corrected(r, 'Toshiba', 'Protage R830') == 'Portege R830'
    assert corrected(r, 'Toshiba', 'Tecar A12') == 'Tecra A12'                   # the usual near miss (two products suffice)
    assert corrected(r, 'Toshiba', 'Tarce A12') is None                          # looser than that: Tecra is on two products only
