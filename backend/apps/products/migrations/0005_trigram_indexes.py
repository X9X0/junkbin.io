"""
Enable pg_trgm extension and add GIN trigram indexes on searchable text fields.

These indexes accelerate icontains (LIKE '%term%') queries automatically.
Also backfills search_vector for existing Product rows.
"""
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0004_search_optimization"),
        ("components", "0004_search_optimization"),
    ]

    operations = [
        # Enable pg_trgm extension
        TrigramExtension(),

        # Trigram indexes for Product text fields
        migrations.RunSQL(
            sql='CREATE INDEX IF NOT EXISTS '
                'idx_product_manufacturer_trgm ON products_product '
                'USING gin (manufacturer gin_trgm_ops);',
            reverse_sql='DROP INDEX IF EXISTS idx_product_manufacturer_trgm;',
            state_operations=[],
        ),
        migrations.RunSQL(
            sql='CREATE INDEX IF NOT EXISTS '
                'idx_product_model_number_trgm ON products_product '
                'USING gin (model_number gin_trgm_ops);',
            reverse_sql='DROP INDEX IF EXISTS idx_product_model_number_trgm;',
            state_operations=[],
        ),
        migrations.RunSQL(
            sql='CREATE INDEX IF NOT EXISTS '
                'idx_product_description_trgm ON products_product '
                'USING gin (description gin_trgm_ops);',
            reverse_sql='DROP INDEX IF EXISTS idx_product_description_trgm;',
            state_operations=[],
        ),
        migrations.RunSQL(
            sql='CREATE INDEX IF NOT EXISTS '
                'idx_product_fcc_id_trgm ON products_product '
                'USING gin (fcc_id gin_trgm_ops);',
            reverse_sql='DROP INDEX IF EXISTS idx_product_fcc_id_trgm;',
            state_operations=[],
        ),

        # Trigram indexes for Component text fields
        migrations.RunSQL(
            sql='CREATE INDEX IF NOT EXISTS '
                'idx_component_part_number_trgm ON components_component '
                'USING gin (part_number gin_trgm_ops);',
            reverse_sql='DROP INDEX IF EXISTS idx_component_part_number_trgm;',
            state_operations=[],
        ),
        migrations.RunSQL(
            sql='CREATE INDEX IF NOT EXISTS '
                'idx_component_manufacturer_trgm ON components_component '
                'USING gin (manufacturer gin_trgm_ops);',
            reverse_sql='DROP INDEX IF EXISTS idx_component_manufacturer_trgm;',
            state_operations=[],
        ),
        migrations.RunSQL(
            sql='CREATE INDEX IF NOT EXISTS '
                'idx_component_description_trgm ON components_component '
                'USING gin (description gin_trgm_ops);',
            reverse_sql='DROP INDEX IF EXISTS idx_component_description_trgm;',
            state_operations=[],
        ),
        migrations.RunSQL(
            sql='CREATE INDEX IF NOT EXISTS '
                'idx_component_typical_function_trgm ON components_component '
                'USING gin (typical_function gin_trgm_ops);',
            reverse_sql='DROP INDEX IF EXISTS idx_component_typical_function_trgm;',
            state_operations=[],
        ),

        # Backfill search vectors for existing rows
        migrations.RunSQL(
            sql="""
                UPDATE products_product SET search_vector =
                    setweight(to_tsvector('english', coalesce(manufacturer, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(model_number, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(fcc_id, '')), 'B') ||
                    setweight(to_tsvector('english', coalesce(description, '')), 'C');
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""
                UPDATE components_component SET search_vector =
                    setweight(to_tsvector('english', coalesce(part_number, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(manufacturer, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(typical_function, '')), 'B') ||
                    setweight(to_tsvector('english', coalesce(description, '')), 'C');
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
