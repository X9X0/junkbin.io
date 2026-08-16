"""
Unit tests for apps.products.bom_utils column mapping.
"""
from apps.products.bom_utils import detect_column_mapping


class TestDetectColumnMapping:
    def test_recognizes_standard_headers(self):
        mapping = detect_column_mapping(['Reference Designator', 'Part Number', 'Manufacturer'])
        assert mapping == {
            'Reference Designator': 'reference_designator',
            'Part Number': 'part_number',
            'Manufacturer': 'manufacturer',
        }

    def test_recognizes_ref_no_variants(self):
        # "Ref.No." is common in Japanese-manufacturer service manual
        # replacement parts lists (e.g. Panasonic).
        for header in ('Ref.No.', 'Ref No.', 'Ref No', 'Ref. No.'):
            mapping = detect_column_mapping([header, 'Part No.'])
            assert mapping.get(header) == 'reference_designator', header
