"""
Tests for apps.components.tasks.enrich_component.
"""
from unittest.mock import patch

import pytest

from apps.components.tasks import enrich_component

pytestmark = pytest.mark.django_db


class TestEnrichComponent:
    def test_fills_description_when_empty(self, component_factory):
        component = component_factory(description='', datasheet_url='', octopart_url='')
        result = {
            'mpn': component.part_number,
            'manufacturer': component.manufacturer,
            'description': 'Operational Amplifiers - Op Amps Dual',
            'datasheet_url': 'https://example.com/datasheet.pdf',
            'specs': [],
            'sellers': [],
        }

        with patch('apps.components.lookup.lookup_part', return_value=result):
            enrich_component.run(component.id)

        component.refresh_from_db()
        assert component.description == 'Operational Amplifiers - Op Amps Dual'
        assert component.datasheet_url == 'https://example.com/datasheet.pdf'
        assert component.specifications['nexar_data']['mpn'] == component.part_number

    def test_does_not_overwrite_existing_description(self, component_factory):
        component = component_factory(description='Hand-verified description')
        result = {
            'mpn': component.part_number,
            'manufacturer': component.manufacturer,
            'description': 'Some Nexar Category',
            'datasheet_url': None,
            'specs': [],
            'sellers': [],
        }

        with patch('apps.components.lookup.lookup_part', return_value=result):
            enrich_component.run(component.id)

        component.refresh_from_db()
        assert component.description == 'Hand-verified description'

    def test_no_results_leaves_component_untouched(self, component_factory):
        component = component_factory(description='')

        with patch('apps.components.lookup.lookup_part', return_value=None):
            enrich_component.run(component.id)

        component.refresh_from_db()
        assert component.description == ''
