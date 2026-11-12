# Case-insensitive lookups of a component by maker and part number (manufacturer__iexact,
# part_number__iexact: the importers, external add, cross-reference matching) were a
# sequential scan over the whole table (~30 ms each at 35k rows). This expression index
# serves the UPPER(...) = UPPER(...) form Django emits for iexact on PostgreSQL.
from django.db import migrations, models
from django.db.models.functions import Upper


class Migration(migrations.Migration):

    dependencies = [
        ('components', '0017_alter_component_component_type_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='component',
            index=models.Index(Upper('manufacturer'), Upper('part_number'), name='component_upper_maker_pn_idx'),
        ),
    ]
