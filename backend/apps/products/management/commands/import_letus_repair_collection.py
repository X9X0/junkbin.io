"""
Management command to import a curated batch of schematics/boardviews from
the letus.repair mirror (see /home/scap/Norway on the mirror VM) into
Product/Schematic records here.

This is a hand-picked "most popular products" subset (~60 products), not the
full 218k-file mirror -- see /home/scap/Norway/junkbin_import/manifest.json
for how that subset was chosen. Each product's schematics are capped at 6
files, largest-first, restricted to extensions Schematic.file's own
FileExtensionValidator allows (so nothing here is structurally inconsistent
with what a real user could upload through the site).

Idempotent: reruns skip products/schematics that already exist (matched on
manufacturer+model_number, and source_url per schematic), so this is safe to
run again after --flush or after extending the manifest.

Every product/schematic creation (or skip) is also emitted as a single
"TRACK: {json}" line on stdout, in addition to the normal human-readable
progress lines -- the external tracking ledger (outside this repo, since
which environment things get pushed to and when isn't this app's concern)
parses those lines to know what happened on this run, in which environment.

Usage:
    python manage.py import_letus_repair_collection --manifest /path/to/manifest.json --files-dir /path/to/files --environment dev
    python manage.py import_letus_repair_collection --manifest ... --files-dir ... --environment prod --dry-run
    python manage.py import_letus_repair_collection --manifest ... --files-dir ... --environment dev --flush
"""
import json
import os

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.products.models import Product, Schematic

User = get_user_model()

NOTES_PREFIX = "[letus.repair mirror import]"


class Command(BaseCommand):
    help = "Import a curated batch of schematics from the letus.repair mirror."

    def add_arguments(self, parser):
        parser.add_argument("--manifest", required=True, help="Path to manifest.json")
        parser.add_argument("--files-dir", required=True, help="Directory containing the staged schematic files")
        parser.add_argument(
            "--environment", required=True, choices=["dev", "prod"],
            help="Which environment this run is against -- for tracking output only, "
                 "does not change any behavior (that's controlled by Django settings/DB connection).",
        )
        parser.add_argument("--flush", action="store_true",
                             help="Delete previously-imported schematics from this batch (matched by source_notes prefix) before re-importing.")
        parser.add_argument("--dry-run", action="store_true",
                             help="Show what would be created without writing to the database.")

    @transaction.atomic
    def handle(self, *args, **options):
        manifest_path = options["manifest"]
        files_dir = options["files_dir"]
        environment = options["environment"]
        dry_run = options["dry_run"]

        if not os.path.isfile(manifest_path):
            raise CommandError(f"manifest not found: {manifest_path}")
        if not os.path.isdir(files_dir):
            raise CommandError(f"files-dir not found: {files_dir}")

        with open(manifest_path) as f:
            manifest = json.load(f)

        admin = self._get_or_create_admin(dry_run)

        if options["flush"]:
            self._flush(dry_run, environment)

        totals = {"products_created": 0, "products_existing": 0,
                  "schematics_created": 0, "schematics_skipped": 0, "schematics_failed": 0}

        for pdata in manifest["products"]:
            self._import_product(pdata, files_dir, admin, dry_run, environment, totals)

        self.stdout.write(
            f"Products: {totals['products_created']} created, {totals['products_existing']} already existed. "
            f"Schematics: {totals['schematics_created']} created, {totals['schematics_skipped']} skipped "
            f"(already existed), {totals['schematics_failed']} failed."
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run -- no changes written."))
            transaction.set_rollback(True)
        else:
            self.stdout.write(self.style.SUCCESS("Import complete."))

    # ------------------------------------------------------------------

    def _get_or_create_admin(self, dry_run):
        admin = User.objects.filter(is_superuser=True).order_by("date_joined").first()
        if admin:
            return admin
        if dry_run:
            return User(username="admin")
        admin = User.objects.create_superuser(
            username="admin", email="admin@junkbin.local", password="admin",
        )
        admin.email_verified = True
        admin.save(update_fields=["email_verified"])
        self.stdout.write(self.style.WARNING("Created default admin user (admin / admin)."))
        return admin

    def _flush(self, dry_run, environment):
        qs = Schematic.objects.filter(source_notes__startswith=NOTES_PREFIX)
        count = qs.count()
        if count and not dry_run:
            qs.delete()
        self.stdout.write(self.style.WARNING(f"Flushed {count} previously-imported schematic(s)."))
        self._track({"event": "flush", "environment": environment, "count": count})

    def _import_product(self, pdata, files_dir, admin, dry_run, environment, totals):
        product, was_new = Product.objects.get_or_create(
            manufacturer=pdata["manufacturer"],
            model_number=pdata["model_number"],
            defaults={
                "category": pdata["category"],
                "description": pdata.get("description", ""),
                "is_approved": True,
                "created_by": admin,
            },
        )
        totals["products_created" if was_new else "products_existing"] += 1
        self.stdout.write(
            f"Product: {product.manufacturer} {product.model_number} "
            f"({'created' if was_new else 'already existed'})"
        )
        self._track({
            "event": "product", "environment": environment,
            "manufacturer": product.manufacturer, "model_number": product.model_number,
            "product_id": str(product.pk), "was_new": was_new,
        })

        for sdata in pdata["schematics"]:
            self._import_schematic(product, sdata, files_dir, admin, dry_run, environment, totals)

    def _import_schematic(self, product, sdata, files_dir, admin, dry_run, environment, totals):
        source_url = sdata["source_url"]
        if Schematic.objects.filter(product=product, source_url=source_url).exists():
            totals["schematics_skipped"] += 1
            self._track({
                "event": "schematic", "environment": environment, "status": "skipped_existing",
                "product_id": str(product.pk), "source_id": sdata["source_id"], "source_url": source_url,
            })
            return

        file_path = os.path.join(files_dir, sdata["local_filename"])
        if not os.path.isfile(file_path):
            totals["schematics_failed"] += 1
            self.stderr.write(self.style.WARNING(f"  file not found, skipping: {file_path}"))
            self._track({
                "event": "schematic", "environment": environment, "status": "failed_missing_file",
                "product_id": str(product.pk), "source_id": sdata["source_id"], "source_url": source_url,
            })
            return

        if dry_run:
            totals["schematics_created"] += 1
            self._track({
                "event": "schematic", "environment": environment, "status": "would_create",
                "product_id": str(product.pk), "source_id": sdata["source_id"], "source_url": source_url,
            })
            return

        with open(file_path, "rb") as fh:
            schematic = Schematic(
                product=product,
                schematic_type=sdata["schematic_type"],
                title=sdata["title"],
                source_type=sdata["source_type"],
                source_url=source_url,
                source_notes=f"{NOTES_PREFIX} {sdata['source_notes']}",
                is_approved=True,
                uploaded_by=admin,
            )
            filename = os.path.basename(sdata["local_filename"])
            schematic.file.save(filename, File(fh), save=False)
            schematic.file_size = os.fstat(fh.fileno()).st_size
            schematic.file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            schematic.save()

        totals["schematics_created"] += 1
        self._track({
            "event": "schematic", "environment": environment, "status": "created",
            "product_id": str(product.pk), "schematic_id": str(schematic.pk),
            "source_id": sdata["source_id"], "source_url": source_url,
        })

    def _track(self, payload):
        self.stdout.write(f"TRACK: {json.dumps(payload)}")
