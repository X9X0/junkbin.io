"""
Import/Export resources for Component and ProductComponent models.

Uses django-import-export to enable admin-side CSV/Excel import and export
with natural key resolution for foreign keys.
"""
import json

from import_export import fields, resources, widgets

from apps.products.models import Product

from .models import Component, ProductComponent


class JSONWidget(widgets.Widget):
    """Serializes JSONField values to/from JSON strings for CSV/Excel."""

    def clean(self, value, row=None, **kwargs):
        if not value or (isinstance(value, str) and not value.strip()):
            return self.default if hasattr(self, 'default') else None
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def render(self, value, obj=None):
        if value is None:
            return ''
        return json.dumps(value, ensure_ascii=False)


class CompositeForeignKeyWidget(widgets.ForeignKeyWidget):
    """
    Resolves foreign keys by composite natural key using '|' separator.

    Examples:
        Product: "Flipper Devices | FZ.1" -> lookup(manufacturer, model_number)
        Component: "Texas Instruments | BQ25896RTWR" -> lookup(manufacturer, part_number)
    """

    def __init__(self, model, lookup_fields, *args, **kwargs):
        # Pass the first lookup field as the 'field' arg for the parent
        super().__init__(model, field=lookup_fields[0], *args, **kwargs)
        self.lookup_fields = lookup_fields

    def clean(self, value, row=None, **kwargs):
        if not value or (isinstance(value, str) and not value.strip()):
            return None
        parts = [p.strip() for p in str(value).split('|')]
        if len(parts) != len(self.lookup_fields):
            raise ValueError(
                f"Expected {len(self.lookup_fields)} values separated by '|', "
                f"got {len(parts)}: {value}"
            )
        lookup = dict(zip(self.lookup_fields, parts))
        try:
            return self.model.objects.get(**lookup)
        except self.model.DoesNotExist:
            raise ValueError(
                f"{self.model.__name__} not found: {lookup}"
            )

    def render(self, value, obj=None):
        if value is None:
            return ''
        parts = [str(getattr(value, f, '')) for f in self.lookup_fields]
        return ' | '.join(parts)


class ComponentResource(resources.ModelResource):
    """Import/Export resource for Component model.

    Uses (manufacturer, part_number) as the natural key so importing
    existing combinations updates rather than duplicates.
    """

    specifications = fields.Field(
        column_name='specifications',
        attribute='specifications',
        widget=JSONWidget(),
    )
    manufacturer_aliases = fields.Field(
        column_name='manufacturer_aliases',
        attribute='manufacturer_aliases',
        widget=JSONWidget(),
    )
    alternative_part_numbers = fields.Field(
        column_name='alternative_part_numbers',
        attribute='alternative_part_numbers',
        widget=JSONWidget(),
    )

    class Meta:
        model = Component
        import_id_fields = ('manufacturer', 'part_number')
        fields = (
            'manufacturer', 'part_number', 'component_type', 'package_type',
            'description', 'typical_function', 'specifications',
            'datasheet_url', 'octopart_url', 'manufacturer_aliases',
            'alternative_part_numbers', 'is_verified', 'usage_count',
        )
        export_order = fields

    def before_import_row(self, row, **kwargs):
        # Strip whitespace on key lookup fields
        for field in ('manufacturer', 'part_number'):
            if field in row and isinstance(row[field], str):
                row[field] = row[field].strip()

    def skip_row(self, instance, original, row, import_validation_errors=None):
        # Skip rows missing required fields
        if not instance.manufacturer or not instance.part_number:
            return True
        return super().skip_row(
            instance, original, row,
            import_validation_errors=import_validation_errors,
        )


class ProductComponentResource(resources.ModelResource):
    """Import/Export resource for ProductComponent model.

    Product and Component foreign keys are rendered as human-readable
    composite keys (e.g. "Flipper Devices | FZ.1").
    Rows with a UUID id update existing records; rows without create new ones.
    """

    product = fields.Field(
        column_name='product',
        attribute='product',
        widget=CompositeForeignKeyWidget(
            Product, lookup_fields=['manufacturer', 'model_number'],
        ),
    )
    component = fields.Field(
        column_name='component',
        attribute='component',
        widget=CompositeForeignKeyWidget(
            Component, lookup_fields=['manufacturer', 'part_number'],
        ),
    )

    class Meta:
        model = ProductComponent
        import_id_fields = ('id',)
        fields = (
            'id', 'product', 'component', 'reference_designator',
            'quantity', 'location_description', 'board_name', 'notes',
            'submission_level', 'is_verified',
        )
        export_order = fields

    def before_import_row(self, row, **kwargs):
        # Strip empty id so Django generates a UUID for new rows
        if 'id' in row and (not row['id'] or str(row['id']).strip() == ''):
            del row['id']
