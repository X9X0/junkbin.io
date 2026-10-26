"""
Import board BOM bundles (one JSON file per board) as a Product with its
components, factory-approved alternates and generic passives.

    manage.py import_board_bom PATH [PATH ...] [--dry-run] [--user NAME] [--skip-components]

PATH is a bundle.json or a directory searched recursively for them. Bundle:

    {
      "bundle_version": 1,
      "source_tag": "norway-bom:<board key>",       # marks everything this import owns
      "source_note": "Factory BOM ... file 12345",
      "product": {"manufacturer", "model_number", "revision", "category",
                  "subcategory", "year_manufactured", "description"},
      "components": [{
          "part_number", "manufacturer", "component_type", "package_type",
          "description", "specifications": {}, "reference_designators": ["U1", ...],
          "quantity", "notes",
          "alternates":  [{"part_number", "manufacturer", "description"}],   # factory-approved second
                                                       # sources; description = the alternate's own BOM line
          "equivalents": [{"part_number", "manufacturer", "component_type",
                           "package_type", "description", "specifications"}]
      }]
    }

Optional "firmware": [{"file", "md5", "title", "description", "version",
"chip_architecture", "source_notes"}] - flash dumps, stored unmodified as the
product's Firmware (unapproved, source type "dumped").

Optional "documents": [{"file": "docs/x.zip" (relative to the bundle), "md5",
"schematic_type", "title", "description", "source_notes"}] become Schematic
records on the product (unapproved, source type leaked). A file whose md5 is
already on the product is not uploaded again; documents this import added
earlier that are no longer in the bundle are removed.

With "attach_to_existing": true, a bundle whose product already exists under
another owner adds its documents to that product and changes nothing else.

Generic passives come through as ordinary components (manufacturer "Generic",
part_number a spec string such as "RES 10K 1% 1/10W 0603") whose
"equivalents" are verified current parts.

Products and BOM rows carry the bundle's source tag in import_source (never
shown on the site). Re-running is safe: a product this command created is found by its source tag
(so a corrected revision or description updates it in place) and its imported
components replaced; a product that already exists without this
bundle's source tag (somebody else's work) is left alone. New products are
created unapproved. Existing components are reused, never edited - except that ratings
and a package they lack are filled in from the BOM line (apps.components.spec_fill).
A new component's description is its own BOM line without the factory's markers and
MAKER/PART echo; its ratings (value, voltage, power, current, tolerance, ...), package
and type are read from that line and checked against its part number.
"""
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.components.models import Component, ProductComponent
from apps.components.spec_fill import fill, plan
from apps.components.spec_parse import clean_bom_text, ic_package
from apps.products.import_text import bom_component_type, clean_text, clean_title
from apps.products.models import Firmware, Product, ProductImage, Schematic

PASSIVE_TYPES = ('resistor', 'capacitor', 'inductor', 'ferrite', 'crystal', 'thermistor', 'fuse')
REFDES_MAX = ProductComponent._meta.get_field('reference_designator').max_length or 100_000


PACKAGE = r'(?:PLCC|SOT|SOD|SOP|SSOP|TSSOP|QFN|DFN|QFP|LQFP|TQFP|BGA|DPAK|D2PAK|TO|SOIC|SO|DIP|SMA|SMB|SMC)-?\d*[A-Z]?'


def alternate_description(primary):
    """'Factory-approved alternate to SST 39VF512-90-4C-NH (eeprom, PLCC32)'."""
    import re
    line = primary.get('description', '').split(';')[0].upper()
    package = re.search(rf'(?<![A-Z0-9])({PACKAGE})(?![A-Z])', line)
    hint = ', '.join(x for x in (primary.get('component_type', '').replace('_', ' '),
                                  package.group(1) if package else '') if x and x != 'other')
    text = f"Factory-approved alternate to {primary['manufacturer']} {primary['part_number']}"
    return f'{text} ({hint})' if hint else text


def full_description(bundle):
    """The product description plus where the data came from (shown on the product page)."""
    return clean_text(f"{bundle['product'].get('description', '')} {bundle.get('source_note', '')}".strip())


def refdes_chunks(refdes, limit=REFDES_MAX):
    """Split a refdes list into ', '-joined strings that fit the column."""
    chunk = []
    for ref in refdes:
        if chunk and len(', '.join(chunk + [ref])) > limit:
            yield chunk
            chunk = []
        chunk.append(ref)
    if chunk:
        yield chunk


class Command(BaseCommand):
    help = 'Import board BOM bundles (products, components, alternates, generic passives)'

    def add_arguments(self, parser):
        parser.add_argument('paths', nargs='+')
        parser.add_argument('--dry-run', action='store_true', help='Report, then roll back')
        parser.add_argument('--user', help='Username recorded as creator (default: first superuser)')
        parser.add_argument('--skip-components', '--documents-only', dest='skip_components',
                            action='store_true',
                            help='On products this import already created, update the product fields '
                                 '(revision, description, ...) and documents; leave components alone')

    def handle(self, *args, **options):
        files = []
        for p in map(Path, options['paths']):
            files += sorted(p.rglob('bundle.json')) if p.is_dir() else [p]
        if not files:
            raise CommandError('no bundle.json found')

        User = get_user_model()
        if options['user']:
            user = User.objects.filter(username=options['user']).first()
            if not user:
                raise CommandError(f"no user {options['user']}")
        else:
            user = User.objects.filter(is_superuser=True).order_by('date_joined').first()

        totals = {'products_created': 0, 'products_updated': 0, 'products_skipped': 0,
                  'components_created': 0, 'placements': 0, 'cross_refs': 0}
        for path in files:
            bundle = json.loads(path.read_text(encoding='utf-8'))
            if bundle.get('bundle_version') != 1:
                raise CommandError(f'{path}: unsupported bundle_version {bundle.get("bundle_version")}')
            try:
                with transaction.atomic():
                    if options['skip_components']:
                        result = self.sync_documents_only(bundle, user, path.parent, options['dry_run'])
                    else:
                        result = self.import_bundle(bundle, user, path.parent, options['dry_run'])
                    if options['dry_run']:
                        raise _Rollback(result)
            except _Rollback as rb:
                result = rb.result
            for k, v in result.items():
                totals[k] = totals.get(k, 0) + v
            self.stdout.write(f"{path.parent.name}: {_fmt(result)}")
        prefix = 'DRY RUN (rolled back) - ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(f'{prefix}{len(files)} bundles: {_fmt(totals)}'))

    def import_bundle(self, bundle, user, folder, dry_run=False):
        tag = bundle['source_tag']
        p = bundle['product']
        result = {'products_created': 0, 'products_updated': 0, 'products_skipped': 0,
                  'components_created': 0, 'placements': 0, 'cross_refs': 0,
                  'documents_added': 0, 'documents_kept': 0, 'documents_removed': 0}
        product = self.find_product(bundle)
        if product is None:
            existing = self.existing_product(bundle)
            if bundle.get('attach_to_existing') and existing:
                # somebody else's product (or another import's): add documents, touch nothing else
                result['products_attached'] = 1
                self.import_documents(bundle, existing, user, folder, dry_run, result)
                self.import_firmware(bundle, existing, user, folder, dry_run, result)
                return result
            result['products_skipped'] = 1
            return result
        if product:
            self.update_identity(product, {**p, 'description': full_description(bundle)})
            product.product_components.filter(import_source=tag).delete()
            result['products_updated'] = 1
        else:
            product = Product.objects.create(
                manufacturer=p['manufacturer'], model_number=p['model_number'],
                revision=p.get('revision', ''), region='global',
                category=p['category'], subcategory=p.get('subcategory', ''),
                year_manufactured=p.get('year_manufactured'),
                description=full_description(bundle), import_source=tag,
                created_by=user, is_approved=False,
            )
            result['products_created'] = 1

        for c in bundle['components']:
            component, created = self.get_component(c, user)
            result['components_created'] += created
            for ref in c.get('alternates', []) + c.get('equivalents', []):
                if 'component_type' in ref and c['manufacturer'] == 'Generic':
                    # a current part suggested for a generic line - not something the factory approved
                    spec = {'specifications': {}, **ref,
                            'description': ref.get('description') or f"Current equivalent of Generic {c['part_number']}"}
                elif ref.get('description'):                # a full record, or an alternate with its own BOM line
                    spec = {'component_type': '', 'specifications': {}, **ref}
                else:                                       # older bundles: describe it as a second source
                    spec = {**c, **ref, 'specifications': {},   # (the BOM line names the primary part)
                            'description': alternate_description(c)}
                other, created = self.get_component(spec, user)
                result['components_created'] += created
                if other.pk != component.pk and not component.cross_references.filter(pk=other.pk).exists():
                    component.cross_references.add(other)
                    result['cross_refs'] += 1
            refs = c.get('reference_designators') or []
            chunks = list(refdes_chunks(refs)) or [[]]
            for chunk in chunks:
                ProductComponent.objects.create(
                    product=product, component=component,
                    reference_designator=', '.join(chunk),
                    quantity=len(chunk) if chunk else c.get('quantity') or 1,
                    notes=clean_text(c.get('notes', '')), import_source=tag,
                    submission_level=ProductComponent.SubmissionLevel.ADVANCED,
                    created_by=user,
                )
                result['placements'] += 1

        product.update_component_count()
        for component in Component.objects.filter(product_components__product=product).distinct():
            component.update_usage_count()
        self.import_documents(bundle, product, user, folder, dry_run, result)
        self.import_images(bundle, product, user, folder, dry_run, result)
        self.import_firmware(bundle, product, user, folder, dry_run, result)
        return result

    @staticmethod
    def find_product(bundle):
        """This import's product (found by source tag, so a corrected revision updates it
        in place), False when there is none yet, None when the name belongs to a product
        somebody else created - which is never touched."""
        p = bundle['product']
        tagged = Product.objects.filter(import_source=bundle['source_tag']).first()
        same_name = Product.objects.filter(
            manufacturer=p['manufacturer'], model_number=p['model_number'],
            revision=p.get('revision', ''), region='global').first()
        if same_name and same_name != tagged:
            return None
        return tagged or False

    @staticmethod
    def existing_product(bundle):
        p = bundle['product']
        return Product.objects.filter(
            manufacturer__iexact=p['manufacturer'], model_number__iexact=p['model_number'],
            revision__iexact=p.get('revision', ''), region='global').first()

    @staticmethod
    def update_identity(product, p):
        fields = {'revision': p.get('revision', ''), 'description': p.get('description', ''),
                  'year_manufactured': p.get('year_manufactured'), 'category': p['category'],
                  'subcategory': p.get('subcategory', '')}
        changed = [k for k, v in fields.items() if getattr(product, k) != v]
        for k in changed:
            setattr(product, k, fields[k])
        if changed:
            product.save(update_fields=changed)

    def sync_documents_only(self, bundle, user, folder, dry_run):
        result = {'products_skipped': 0, 'documents_added': 0, 'documents_kept': 0, 'documents_removed': 0}
        product = self.find_product(bundle)
        if not product:
            result['products_skipped'] = 1
            return result
        self.update_identity(product, {**bundle['product'], 'description': full_description(bundle)})
        self.import_documents(bundle, product, user, folder, dry_run, result)
        self.import_images(bundle, product, user, folder, dry_run, result)
        self.import_firmware(bundle, product, user, folder, dry_run, result)
        return result

    @staticmethod
    def import_images(bundle, product, user, folder, dry_run, result):
        """Bundle "images" (e.g. a document's first page as a cover): added once, unapproved,
        preview image only when the product has no picture yet."""
        for img in bundle.get('images', []):
            if product.images.filter(caption=img['caption'][:200]).exists():
                continue
            result['images_added'] = result.get('images_added', 0) + 1
            if dry_run:
                continue
            path = folder / img['file']
            if not path.is_file():
                raise CommandError(f'{path}: image missing')
            with path.open('rb') as fh:
                ProductImage.objects.create(
                    product=product, image=File(fh, name=f'{product.pk}-cover.jpg'),
                    image_type=img.get('image_type') or ProductImage.ImageType.OTHER,
                    caption=img['caption'][:200], is_primary=not product.images.exists(),
                    uploaded_by=user, is_approved=False)

    @staticmethod
    def import_firmware(bundle, product, user, folder, dry_run, result):
        """Bundle "firmware" (flash dumps, imported unmodified): added once per md5, unapproved;
        files this import added earlier that the bundle no longer lists are removed."""
        tag = bundle['source_tag']
        wanted = {f['md5'] for f in bundle.get('firmware', [])}
        have = {}
        for fw in product.firmware_files.all():
            marker = fw.source_notes.rsplit('md5:', 1)
            if len(marker) == 2:
                have[marker[1].strip()] = fw
        for md5, fw in have.items():
            if fw.source_notes.startswith(f'[{tag}]') and md5 not in wanted:
                if not dry_run:
                    fw.file.delete(save=False)
                    fw.delete()
                result['firmware_removed'] = result.get('firmware_removed', 0) + 1
        for item in bundle.get('firmware', []):
            if item['md5'] in have:
                result['firmware_kept'] = result.get('firmware_kept', 0) + 1
                continue
            path = folder / item['file']
            if not path.is_file():
                raise CommandError(f'{path}: firmware file missing')
            result['firmware_added'] = result.get('firmware_added', 0) + 1
            if dry_run:
                continue
            with path.open('rb') as fh:
                Firmware.objects.create(
                    product=product, file=File(fh, name=path.name),
                    title=clean_title(item['title'])[:300], description=item.get('description', ''),
                    version=item.get('version', '')[:50], chip_architecture=item.get('chip_architecture', '')[:100],
                    source_type=Firmware.SourceType.DUMPED,
                    source_notes=f"[{tag}] {item.get('source_notes', '')} md5:{item['md5']}",
                    uploaded_by=user, is_approved=False,
                )

    @staticmethod
    def import_documents(bundle, product, user, folder, dry_run, result):
        tag = bundle['source_tag']
        wanted = {d['md5'] for d in bundle.get('documents', [])}
        ours = product.schematics.filter(source_notes__startswith=f'[{tag}]')
        have = {}
        for sch in product.schematics.all():
            marker = sch.source_notes.rsplit('md5:', 1)
            if len(marker) == 2:
                have[marker[1].strip()] = sch
        for sch in ours:
            md5 = sch.source_notes.rsplit('md5:', 1)[-1].strip()
            if md5 not in wanted:
                if not dry_run:
                    sch.file.delete(save=False)
                    sch.delete()
                result['documents_removed'] += 1
        for doc in bundle.get('documents', []):
            if doc['md5'] in have:
                result['documents_kept'] += 1
                continue
            path = folder / doc['file']
            if not path.is_file():
                raise CommandError(f'{path}: document missing')
            result['documents_added'] += 1
            if dry_run:
                continue            # nothing written to storage on a dry run
            with path.open('rb') as fh:
                Schematic.objects.create(
                    product=product, file=File(fh, name=path.name),
                    schematic_type=doc.get('schematic_type') or Schematic.SchematicType.OTHER,
                    title=clean_title(doc['title'])[:300], description=doc.get('description', ''),
                    version=product.revision,
                    source_type=Schematic.SourceType.LEAKED,
                    source_notes=f"[{tag}] {doc.get('source_notes', '')} md5:{doc['md5']}",
                    uploaded_by=user, is_approved=False,
                )

    @staticmethod
    def get_component(c, user):
        """The component for a bundle entry. A new one gets its ratings, package and type from its
        own BOM line; an existing one is never edited, except that ratings and a package it lacks
        are filled in from the line."""
        line = c.get('description', '')
        own_line = (c.get('manufacturer') != 'Generic'          # these describe another part's line:
                    and not line.startswith(('Factory-approved alternate', 'Current equivalent')))
        component = Component.objects.filter(
            manufacturer__iexact=c['manufacturer'], part_number__iexact=c['part_number']).first()
        if component:
            if own_line:
                fill(component, line)
            return component, 0
        component = Component(
            manufacturer=c['manufacturer'], part_number=c['part_number'],
            component_type=(bom_component_type(line)
                            if c.get('component_type') in (None, '', 'ic', 'other') and c.get('manufacturer') != 'Generic'
                            else None) or c.get('component_type') or 'other',
            package_type=c.get('package_type', '')[:50],
            description=clean_bom_text(clean_text(line)) if own_line else clean_text(line),
            specifications=c.get('specifications') or {},
            created_by=user,
        )
        if own_line:
            planned = plan(component, line)
            component.specifications, component.package_type = planned['specs'], planned['package']
            if planned['type'] and component.manufacturer != 'Generic':
                component.component_type = planned['type']
            elif not component.package_type and component.component_type not in PASSIVE_TYPES:
                component.package_type = ic_package(line) or ''
        component.save()
        return component, 1


class _Rollback(Exception):
    def __init__(self, result):
        self.result = result


def _fmt(d):
    return ', '.join(f'{k.replace("_", " ")} {v}' for k, v in d.items() if v)
