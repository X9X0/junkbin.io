"""
Management command to seed the database with well-known open-hardware
devices whose schematics/BOMs are officially published under a permissive
license, following the same pattern as import_flipper_bom.py /
import_flipper_schematics.py.

Pilot batch (2026-08-09): Arduino Uno Rev3 and Framework Laptop 13. Both
were chosen because their manufacturer publishes real component-level data
under a license that allows reuse - not scraped from a third party, not
guessed. Every ProductComponent link carries a source_url/source_notes
pointing at the exact official document the part number came from.

Usage:
    python manage.py import_open_hardware_pilot
    python manage.py import_open_hardware_pilot --flush     # remove this batch, then re-add
    python manage.py import_open_hardware_pilot --dry-run   # show what would be created
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.products.models import Product
from apps.components.models import Component, ProductComponent

User = get_user_model()

# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

PRODUCTS = {
    "arduino_uno": {
        "manufacturer": "Arduino",
        "model_number": "Uno Rev3",
        "part_number": "A000066",
        "category": "sbc",
        "year_manufactured": 2011,
        "description": (
            "Open-hardware microcontroller board built around the Atmel/Microchip "
            "ATmega328P. One of the most widely produced and salvaged development "
            "boards in existence - millions in circulation, and its main MCU, "
            "regulator, and USB bridge chip turn up in countless DIY projects."
        ),
        "teardown_notes": (
            "Fully open hardware - Arduino publishes the official schematic, "
            "pinout, and CAD files directly. Reference designators and part "
            "numbers below are read directly from that schematic, not guessed."
        ),
    },
    "framework_13": {
        "manufacturer": "Framework Computer",
        "model_number": "Laptop 13 (12th Gen Intel Core)",
        "category": "laptop",
        "year_manufactured": 2022,
        "description": (
            "Modular, repair-first laptop designed to be disassembled with a "
            "single screwdriver. Framework publishes mainboard schematics, "
            "connector pinouts, and part numbers so third parties can source "
            "compatible replacement parts - a rare case of a manufacturer "
            "actively supporting the exact thing junkbin.io exists for."
        ),
        "teardown_notes": (
            "Connector part numbers below come from Framework's own Mainboard "
            "README (github.com/FrameworkComputer/Framework-Laptop-13), which "
            "is licensed CC BY 4.0. Note: the Connectors/ subfolder in that same "
            "repo contains third-party vendor datasheets that are explicitly "
            "NOT covered by that license (\"shared only for reference\") - none "
            "of that datasheet content is reproduced here, only the part "
            "numbers and pinout tables from the CC-BY-licensed README."
        ),
    },
}

# ---------------------------------------------------------------------------
# Components: (component dict, link dict) pairs per product
# ---------------------------------------------------------------------------

ARDUINO_SOURCE_URL = "https://docs.arduino.cc/resources/schematics/A000066-schematics.pdf"
ARDUINO_SOURCE_NOTES = (
    "Reference designator and part number read directly from Arduino's "
    "official Uno Rev3 schematic PDF."
)

FRAMEWORK_SOURCE_URL = (
    "https://github.com/FrameworkComputer/Framework-Laptop-13/blob/main/Mainboard/"
    "Mainboard_Interfaces_Schematic_12th_Gen.pdf"
)
FRAMEWORK_SOURCE_NOTES = (
    "Part number read directly from Framework Computer Inc.'s official 12th Gen "
    "mainboard interfaces schematic, published under CC BY 4.0."
)
FRAMEWORK_README_URL = (
    "https://github.com/FrameworkComputer/Framework-Laptop-13/blob/main/Mainboard/README.md"
)
FRAMEWORK_README_NOTES = (
    "Published by Framework Computer Inc. under CC BY 4.0 in the official Mainboard README."
)

ARDUINO_COMPONENTS = [
    {
        "manufacturer": "Microchip Technology",
        "part_number": "ATMEGA328P-PU",
        "component_type": "mcu",
        "package_type": "DIP-28",
        "typical_function": "Main microcontroller",
        "description": (
            "8-bit AVR microcontroller, 32KB flash. Originally an Atmel part "
            "(Atmel was acquired by Microchip in 2016); still sold under both "
            "brandings depending on production date."
        ),
        "specifications": {"flash": "32KB", "architecture": "AVR 8-bit"},
        "reference_designator": "U1",
        "quantity": 1,
        "location_description": "Center of board, socketed DIP package",
    },
    {
        "manufacturer": "Microchip Technology",
        "part_number": "ATMEGA16U2-MU",
        "component_type": "mcu",
        "package_type": "QFN-32",
        "typical_function": "USB-to-serial bridge",
        "description": (
            "Second, smaller AVR MCU dedicated to USB communication with the "
            "host computer - handles the USB-to-serial bridging that lets the "
            "Uno appear as a COM port."
        ),
        "specifications": {"architecture": "AVR 8-bit"},
        "reference_designator": "U3",
        "quantity": 1,
        "location_description": "Near the USB-B connector",
    },
    {
        "manufacturer": "onsemi",
        "part_number": "NCP1117ST50T3G",
        "component_type": "regulator",
        "package_type": "SOT-223",
        "typical_function": "5V linear regulator",
        "description": "Fixed 5V linear voltage regulator, 1A, powers the board from the barrel jack/VIN.",
        "specifications": {"output_voltage": "5V", "max_current": "1A"},
        "reference_designator": "U5",
        "quantity": 1,
        "location_description": "Near the DC barrel jack",
    },
    {
        "manufacturer": "Murata",
        "part_number": "CSTCE16M0V53-R0",
        "component_type": "crystal",
        "package_type": "SMD-3",
        "typical_function": "16MHz clock resonator",
        "description": "16MHz ceramic resonator with built-in load capacitors. One clocks the main MCU, one clocks the USB bridge MCU.",
        "specifications": {"frequency": "16MHz"},
        "reference_designator": "X1, X2",
        "quantity": 2,
        "location_description": "Adjacent to each MCU",
    },
    {
        "manufacturer": "Bel Fuse",
        "part_number": "MF-MSMF050-2",
        "component_type": "fuse",
        "package_type": "SMD",
        "typical_function": "Resettable PTC fuse",
        "description": "500mA resettable polymer fuse protecting the USB VBUS line from overcurrent.",
        "specifications": {"hold_current": "500mA"},
        "reference_designator": "F1",
        "quantity": 1,
        "location_description": "In series with USB VBUS",
    },
    {
        "manufacturer": "onsemi",
        "part_number": "FDN340P",
        "component_type": "mosfet",
        "package_type": "SOT-23",
        "typical_function": "USB power switch",
        "description": (
            "P-channel MOSFET, originally a Fairchild Semiconductor part "
            "(Fairchild was acquired by ON Semiconductor/onsemi in 2016). "
            "Switches power source between USB and external supply."
        ),
        "specifications": {"channel": "P-channel"},
        "reference_designator": "Q1",
        "quantity": 1,
        "location_description": "Near the power selection circuitry",
    },
]

FRAMEWORK_COMPONENTS = [
    {
        "manufacturer": "Infineon (Cypress)",
        "part_number": "CYPD6227",
        "component_type": "ic",
        "package_type": "QFN",
        "typical_function": "USB-C Power Delivery controller",
        "description": (
            "EZ-PD USB-C PD controller, one per USB-C port (4 total on this "
            "board). Genuinely reusable outside the laptop - a common building "
            "block in DIY USB-C PD projects."
        ),
        "specifications": {},
        "reference_designator": "",
        "quantity": 4,
        "location_description": "One beside each of the four USB-C ports",
    },
    {
        "manufacturer": "Renesas (Intersil)",
        "part_number": "ISL9241",
        "component_type": "ic",
        "package_type": "QFN-28",
        "typical_function": "Buck-boost battery charger IC",
        "description": "2-4 cell buck-boost battery charger/system power selector, manages charging from any of the USB-C ports.",
        "specifications": {},
        "reference_designator": "",
        "quantity": 1,
        "location_description": "Power delivery / charging circuitry",
    },
    {
        "manufacturer": "Microchip Technology",
        "part_number": "MEC1521",
        "component_type": "mcu",
        "package_type": "QFN",
        "typical_function": "Embedded controller (EC)",
        "description": (
            "The laptop's embedded controller - handles power sequencing, "
            "keyboard scanning, lid switch, and fan control independent of "
            "the main CPU. The 'brain' behind basic laptop functions even "
            "when the main system is off."
        ),
        "specifications": {},
        "reference_designator": "",
        "quantity": 1,
        "location_description": "Near battery/RTC circuitry",
    },
    {
        "manufacturer": "Capella Microsystems",
        "part_number": "CM32181",
        "component_type": "sensor",
        "package_type": "OPLGA",
        "typical_function": "Ambient light sensor",
        "description": "I2C ambient light sensor used for automatic display brightness. Small, cheap, and popular in DIY light-sensing projects.",
        "specifications": {"interface": "I2C"},
        "reference_designator": "",
        "quantity": 1,
        "location_description": "Near display/webcam circuitry",
    },
    {
        "manufacturer": "MiraMEMS",
        "part_number": "DA217S",
        "component_type": "sensor",
        "package_type": "LGA",
        "typical_function": "3-axis accelerometer",
        "description": "I2C 3-axis accelerometer, used for lid-angle/orientation sensing.",
        "specifications": {"interface": "I2C", "axes": 3},
        "reference_designator": "",
        "quantity": 1,
        "location_description": "Near display/webcam circuitry",
    },
    {
        "manufacturer": "Realtek",
        "part_number": "ALC295",
        "component_type": "ic",
        "package_type": "QFN",
        "typical_function": "Audio codec",
        "description": "HD audio codec driving the speakers and headphone jack. A well-known, widely reused laptop audio codec.",
        "specifications": {},
        "reference_designator": "UA1",
        "quantity": 1,
        "location_description": "Audio circuitry",
    },
    {
        "manufacturer": "Nuvoton (Fintek)",
        "part_number": "F75303M",
        "component_type": "sensor",
        "package_type": "SOP-8",
        "typical_function": "Remote thermal sensor",
        "description": "Remote-diode temperature monitor IC used for CPU/board thermal monitoring.",
        "specifications": {},
        "reference_designator": "UTH1",
        "quantity": 1,
        "location_description": "Thermal monitoring circuitry",
    },
    {
        "manufacturer": "Nuvoton",
        "part_number": "NPCT750AADYX",
        "component_type": "ic",
        "package_type": "QFN",
        "typical_function": "TPM 2.0 module",
        "description": "Discrete Trusted Platform Module (TPM 2.0) security chip.",
        "specifications": {},
        "reference_designator": "UX1",
        "quantity": 1,
        "location_description": "Security/trust circuitry",
        "source_url": FRAMEWORK_SOURCE_URL,
        "source_notes": FRAMEWORK_SOURCE_NOTES,
    },
    {
        "manufacturer": "Intel",
        "part_number": "JHL8040R",
        "component_type": "ic",
        "package_type": "BGA",
        "typical_function": "Thunderbolt 4 retimer",
        "description": (
            "Thunderbolt 4 retimer, one per USB-C port (4 total). Publicly "
            "known by Intel's own codename 'Burnside Bridge', which appears "
            "directly as a schematic block label next to each instance."
        ),
        "specifications": {},
        "reference_designator": "",
        "quantity": 4,
        "location_description": "One beside each of the four USB-C ports",
    },
    {
        "manufacturer": "Anpec Electronics",
        "part_number": "APW8743CQBI",
        "component_type": "ic",
        "package_type": "QFN",
        "typical_function": "VRM controller",
        "description": "Voltage regulator controller for the CPU's +1.05V processor rail.",
        "specifications": {},
        "reference_designator": "UC6",
        "quantity": 1,
        "location_description": "CPU voltage-regulator (VRM) section",
    },
    {
        "manufacturer": "Richtek Technology",
        "part_number": "RT8207PGQW",
        "component_type": "ic",
        "package_type": "QFN",
        "typical_function": "Synchronous buck controller",
        "description": "Buck controller for the DDR memory 1.2V rail.",
        "specifications": {},
        "reference_designator": "PUM01",
        "quantity": 1,
        "location_description": "CPU voltage-regulator (VRM) section",
    },
    {
        "manufacturer": "Richtek Technology",
        "part_number": "RT3624BEGQW",
        "component_type": "ic",
        "package_type": "QFN",
        "typical_function": "Multiphase VRM controller",
        "description": "Multiphase voltage-regulator controller for the CPU core voltage (VCORE) rail.",
        "specifications": {},
        "reference_designator": "PUZ1",
        "quantity": 1,
        "location_description": "CPU voltage-regulator (VRM) section",
    },
    {
        "manufacturer": "Alpha & Omega Semiconductor",
        "part_number": "AOZ5038QI",
        "component_type": "ic",
        "package_type": "QFN",
        "typical_function": "DrMOS power stage",
        "description": "Integrated MOSFET + driver power stage, one of four phases driving the CPU core voltage (VCORE) rail.",
        "specifications": {},
        "reference_designator": "PUZ2, PUZ3, PUZ4, PUZ5",
        "quantity": 4,
        "location_description": "CPU voltage-regulator (VRM) section",
    },
    {
        "manufacturer": "Monolithic Power Systems",
        "part_number": "MP2961GL-Z",
        "component_type": "ic",
        "package_type": "QFN",
        "typical_function": "Buck regulator",
        "description": "Buck regulator for the CPU's VCCIN_AUX rail.",
        "specifications": {},
        "reference_designator": "PUX1",
        "quantity": 1,
        "location_description": "CPU voltage-regulator (VRM) section",
    },
    {
        "manufacturer": "Alpha & Omega Semiconductor",
        "part_number": "AOZ5016QI",
        "component_type": "ic",
        "package_type": "QFN",
        "typical_function": "DrMOS power stage",
        "description": "Integrated MOSFET + driver power stage for the integrated graphics (VCC_GT) rail.",
        "specifications": {},
        "reference_designator": "PUG1, PUG2",
        "quantity": 2,
        "location_description": "CPU voltage-regulator (VRM) section",
    },
    {
        "manufacturer": "Panasonic",
        "part_number": "ML1220",
        "component_type": "battery",
        "package_type": "Coin cell",
        "typical_function": "RTC backup battery",
        "description": (
            "Rechargeable lithium coin cell for real-time-clock backup. "
            "Framework's mainboard trickle-charges this cell - a standard "
            "non-rechargeable CR2032 must NOT be substituted, it cannot be "
            "charged and will likely be damaged. Pin-compatible rechargeable "
            "ML1220-family cells from other manufacturers (Seiko, etc.) work too."
        ),
        "specifications": {"rechargeable": True, "warning": "Do not substitute CR2032"},
        "reference_designator": "",
        "quantity": 1,
        "location_description": "RTC battery interface",
        "source_url": FRAMEWORK_README_URL,
        "source_notes": FRAMEWORK_README_NOTES,
    },
]

BATCHES = [
    ("arduino_uno", ARDUINO_COMPONENTS, ARDUINO_SOURCE_URL, ARDUINO_SOURCE_NOTES),
    ("framework_13", FRAMEWORK_COMPONENTS, FRAMEWORK_SOURCE_URL, FRAMEWORK_SOURCE_NOTES),
]

NOTES_PREFIX = "[Open Hardware Pilot Import]"


class Command(BaseCommand):
    help = "Seed well-known open-hardware devices (Arduino Uno, Framework Laptop 13) with officially-sourced component data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush", action="store_true",
            help="Delete this batch's ProductComponent links (and the products themselves) before re-importing.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what would be created without writing to the database.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        admin = self._get_or_create_admin(dry_run)

        if options["flush"]:
            self._flush(dry_run)

        for key, components, source_url, source_notes in BATCHES:
            self._import_batch(key, components, source_url, source_notes, admin, dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run - no changes written."))
            transaction.set_rollback(True)
        else:
            self.stdout.write(self.style.SUCCESS("Open hardware pilot batch imported successfully."))

    # ------------------------------------------------------------------

    def _get_or_create_admin(self, dry_run):
        admin = User.objects.filter(is_superuser=True).order_by("date_joined").first()
        if admin:
            return admin
        if dry_run:
            return User(username="admin")  # unsaved placeholder, fine for a dry run
        admin = User.objects.create_superuser(
            username="admin", email="admin@junkbin.local", password="admin",
        )
        admin.email_verified = True
        admin.save(update_fields=["email_verified"])
        self.stdout.write(self.style.WARNING("Created default admin user (admin / admin)."))
        return admin

    def _flush(self, dry_run):
        count = 0
        for key, data in PRODUCTS.items():
            qs = Product.objects.filter(
                manufacturer=data["manufacturer"], model_number=data["model_number"],
            )
            n = qs.count()
            if n and not dry_run:
                qs.delete()
            count += n
        self.stdout.write(self.style.WARNING(f"Flushed {count} product(s) (and their component links via cascade)."))

    def _import_batch(self, key, components, source_url, source_notes, admin, dry_run):
        pdata = PRODUCTS[key]
        product, was_new = Product.objects.get_or_create(
            manufacturer=pdata["manufacturer"],
            model_number=pdata["model_number"],
            defaults={
                "part_number": pdata.get("part_number", ""),
                "category": pdata["category"],
                "year_manufactured": pdata.get("year_manufactured"),
                "description": pdata.get("description", ""),
                "teardown_notes": pdata.get("teardown_notes", ""),
                "is_approved": True,
                "created_by": admin,
            },
        )
        self.stdout.write(
            f"Product: {product.manufacturer} {product.model_number} "
            f"({'created' if was_new else 'already existed'})"
        )

        created_components = 0
        reused_components = 0
        created_links = 0
        skipped_links = 0

        for c in components:
            component, was_created = Component.objects.get_or_create(
                manufacturer=c["manufacturer"],
                part_number=c["part_number"],
                defaults={
                    "component_type": c["component_type"],
                    "package_type": c["package_type"],
                    "typical_function": c["typical_function"],
                    "description": c["description"],
                    "specifications": c["specifications"],
                    "is_verified": True,
                    "created_by": admin,
                },
            )
            if was_created:
                created_components += 1
            else:
                reused_components += 1

            link_exists = ProductComponent.objects.filter(
                product=product,
                component=component,
                location_description=c["location_description"],
            ).exists()
            if link_exists:
                skipped_links += 1
                continue

            link_notes = c.get("source_notes", source_notes)
            link_source = c.get("source_url", source_url)
            ProductComponent.objects.create(
                product=product,
                component=component,
                reference_designator=c["reference_designator"],
                quantity=c["quantity"],
                location_description=c["location_description"],
                notes=f"{NOTES_PREFIX} {link_notes} Source: {link_source}",
                submission_level=ProductComponent.SubmissionLevel.BASIC,
                created_by=admin,
            )
            created_links += 1

        self.stdout.write(
            f"  Components: {created_components} created, {reused_components} reused. "
            f"Links: {created_links} created, {skipped_links} skipped (already existed)."
        )
