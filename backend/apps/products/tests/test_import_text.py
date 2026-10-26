"""
Tests for import text cleaning (apps.products.import_text) and clean_import_text.
"""
from io import StringIO

import pytest
from django.core.management import call_command

from apps.products.import_text import bom_component_type, clean_description, clean_text, clean_title, has_cjk


@pytest.mark.parametrize('raw, expected', [
    ('CHOKE立1.1UH/30A T5053B', 'CHOKE vertical 1.1UH/30A T5053B'),
    ('P CHOKE臥0.4UH/40A', 'P CHOKE horizontal 0.4UH/40A'),
    ('FLASH SST 49LF004 PLCC32 燒 ##', 'FLASH SST 49LF004 PLCC32 (pre-programmed) ##'),
    ('marking 此料無需marking', 'marking no marking required'),
    ('marking ..JC..；..A1..', 'marking ..JC..;..A1..'),
    ('DIODE-ZENER;RLZ8.2B,LL-', 'DIODE-ZENER;RLZ8.2B,LL-'),                # hyphens are data
    ('CAP 0.1UF/25V (0603) Y5V 名碩電腦(蘇州)有限公司(MAINTEK)(C) 單階材料用量明細表 製表日期:04/05/26 '
     '頁次:27 主件料號:60-M8LCC0-A0 ; marking x', 'CAP 0.1UF/25V (0603) Y5V; marking x'),
])
def test_clean_text(raw, expected):
    assert clean_text(raw) == expected
    assert clean_text(expected) == expected                                 # idempotent


def test_clean_title_drops_download_site_junk():
    assert clean_title('chinafix.com.cn迅维网_uP7704') == 'uP7704'
    assert clean_title('P75N02LDG (1)_DiskStation_Dec-18-1559-2023_DownloadConflict') == 'P75N02LDG'
    assert clean_title('GA-P31-DS3L-R1.0电路图') == 'GA-P31-DS3L-R1.0 schematic'
    assert not has_cjk(clean_title('Emerson_23.6寸LED_P2289WDI'))


def test_clean_description_from_datasheet_title_page():
    raw = (' 捷多邦，您值得信赖的PCB打样专家！ F71858AD F71858AD Hardware Monitor, KBC with GPIO & ACPI '
           'Release Date: Aug, 2010 Version: V0.12P Aug, 2010 V0.12P')
    assert clean_description(raw, part_number='F71858AD') == 'Hardware Monitor, KBC with GPIO & ACPI'
    assert clean_description('注文コード No. N 2 9 7 7 2SC4478 大信号トランジスタ') == ''   # no English left


@pytest.mark.parametrize('pn, raw, title', [
    ('MAX1602', '19-1125;; 9/96 Single-Channel CardBus and PCMCIA VCC/VPP Power-Switching Network '
                '_______________General Description ____________________________Features',
     'Single-Channel CardBus and PCMCIA VCC/VPP Power-Switching Network'),
    ('MAX1617', '19-1265;; 3/98 KIT ATION EVALU B L E AVAIL A Remote/Local Temperature Sensor with SMBus Serial '
                'Interface ______General Description',
     'Remote/Local Temperature Sensor with SMBus Serial Interface'),
    ('ISL6612', '® ISL6612, ISL6613 February 26, 2007 FN9153.8 Advanced Synchronous Rectified Buck Features MOSFET '
                'Drivers with Protection Features • Pin-to-pin Compatible',
     'Advanced Synchronous Rectified Buck MOSFET Drivers with Protection'),
    ('SN7400', 'SN5400, SN54LS00, SN54S00 SN7400, SN74LS00, SN74S00 QUADRUPLE 2-INPUT POSITIVE-NAND GATES '
               'PRODUCTION DATA information is current', 'QUADRUPLE 2-INPUT POSITIVE-NAND GATES'),
    ('FAN7382', 'FAN7382 Half-Bridge Gate-Driver IC FAN7382 Half-Bridge Gate-Driver IC Features Description',
     'Half-Bridge Gate-Driver IC'),
    ('2SC4921', 'NPN Epitaxial Planar Silicon Transistor 2SC4921 Muting Circuit, Driver Applications Features Package '
                'Dimensions · High DC current gain.',
     'NPN Epitaxial Planar Silicon Transistor 2SC4921 Muting Circuit, Driver Applications'),
    ('G950', 'Global Mixed-mode Technology Inc. G950 2.5V 1A Regulator Features General Description',
     '2.5V 1A Regulator'),
    ('ISL6265', 'ISL6265 ESIGNS ® O R NEW D E D F PART R E C O MMEND PLACEMENT N OT DR E MENDE May 13, 2009', ''),
])
def test_datasheet_title(pn, raw, title):
    assert clean_description(raw, part_number=pn) == title
    assert clean_description(title, part_number=pn) == title             # idempotent


@pytest.mark.parametrize('line, kind', [
    ('P MLCC 33PF/50V (0402)NPO 5% YAGEO/CC0402JRNPO9BN330', 'capacitor'),
    ('ZIF 478P uPGA DIP,G/F LOTES/Z4970ZP3L-E', 'socket'),
    ('SLOT 164P,PCI EXPRESS X16 G/F LOTES', 'connector'),
    ('P SW REG. L6916D SO-28 ST', 'regulator'),
    ('POWER CON 4P S/T,ATX', 'connector'),
    ('HEATSINK 33*33*10mm SILVER', 'other'),
    ('CLOCK Gen. ICS950209CF ICS 48PIN SSOP', None),                       # a chip: the line doesn't say
])
def test_bom_component_type(line, kind):
    assert bom_component_type(line) == kind


@pytest.mark.django_db
def test_clean_import_text_fixes_imported_rows_only(product_factory, component_factory, user_factory):
    from apps.components.models import ProductComponent
    product = product_factory(import_source='norway-bom:X')
    comp = component_factory(component_type='ic', description='P MLCC 0.1UF/16V 立')
    imported = ProductComponent.objects.create(product=product, component=comp, import_source='norway-bom:X',
                                               notes='Factory BOM line: P MLCC 0.1UF/16V 立')
    users = ProductComponent.objects.create(product=product_factory(), component=component_factory(),
                                            notes='hand-written 立')
    out = StringIO()
    call_command('clean_import_text', stdout=out)
    imported.refresh_from_db()
    users.refresh_from_db()
    comp.refresh_from_db()
    assert imported.notes == 'Factory BOM line: P MLCC 0.1UF/16V vertical'
    assert users.notes == 'hand-written 立'                                  # contributors' text untouched
    assert comp.component_type == 'capacitor'
    call_command('clean_import_text', stdout=out)                           # second run changes nothing
    assert 'bom notes: 0 changed' in out.getvalue().splitlines()[-1]
