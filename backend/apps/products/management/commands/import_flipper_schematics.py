"""
Management command to import downloaded Flipper Zero schematics and datasheets
into the database.

Usage:
    python manage.py import_flipper_schematics
    python manage.py import_flipper_schematics --flush  # Delete existing and re-import
"""
import os
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.products.models import Product, Schematic
from apps.components.models import Component

User = get_user_model()

# Schematics to import, grouped by type
SCHEMATICS = [
    # Main PCB schematics
    {
        "file": "schematics/main-pcb-full-schematic.pdf",
        "title": "Flipper Zero Main PCB Full Schematic",
        "schematic_type": "full_schematic",
        "description": "Complete 7-page schematic of the Flipper Zero main PCB (Rev 1.1 F7B9C6). Covers MCU, power management, sub-GHz radio, LCD, buttons, peripherals, and all passive components.",
        "source_type": "official",
        "source_url": "https://docs.flipper.net/zero/development/hardware/schematic",
        "source_notes": "Published by Flipper Devices Inc. via ST Community forums. Schematic revision 1.1, PCB reference F7B9C6.",
        "repair_relevance": "Essential for board-level repair. Shows all component connections, power rails, and signal routing for the main PCB.",
        "version": "1.1",
    },
    {
        "file": "schematics/main-pcbmain-blocks.pdf",
        "title": "Main PCB Block Diagram",
        "schematic_type": "block_diagram",
        "description": "High-level block diagram showing the main functional blocks of the Flipper Zero main PCB and their interconnections.",
        "source_type": "official",
        "source_url": "https://docs.flipper.net/zero/development/hardware/schematic",
        "repair_relevance": "Useful for understanding the overall architecture and signal flow between major subsystems.",
    },
    {
        "file": "schematics/mcu-stm32wb55-schematic.pdf",
        "title": "MCU STM32WB55 Schematic",
        "schematic_type": "full_schematic",
        "description": "Detailed schematic of the STM32WB55RGV6 MCU section including crystal oscillators, decoupling, SWD debug port, and all pin connections.",
        "source_type": "official",
        "source_url": "https://docs.flipper.net/zero/development/hardware/schematic",
        "repair_relevance": "Critical for MCU-related fault diagnosis — covers clock circuits, reset, boot pins, and debug interface.",
    },
    {
        "file": "schematics/power-schematic.pdf",
        "title": "Main PCB Power Management Schematic",
        "schematic_type": "full_schematic",
        "description": "Power supply section of the main PCB: battery charger (BQ25896), fuel gauge (BQ27220), LDO regulators, and power distribution to all subsystems.",
        "source_type": "official",
        "source_url": "https://docs.flipper.net/zero/development/hardware/schematic",
        "repair_relevance": "Essential for diagnosing charging failures, battery issues, and voltage rail problems.",
    },
    {
        "file": "schematics/peripherals-schematic.pdf",
        "title": "Peripherals Schematic",
        "schematic_type": "full_schematic",
        "description": "Peripheral interfaces: USB-C connector, microSD card slot, GPIO header, LED driver (LP5562), and antenna switch (SKY13373).",
        "source_type": "official",
        "source_url": "https://docs.flipper.net/zero/development/hardware/schematic",
        "repair_relevance": "Useful for USB-C, SD card, and GPIO troubleshooting.",
    },
    {
        "file": "schematics/lcd-display-schematic.pdf",
        "title": "LCD Display Schematic",
        "schematic_type": "full_schematic",
        "description": "ST7567 LCD controller circuit including SPI interface, backlight driver, and FPC connector pinout for the 128x64 monochrome display.",
        "source_type": "official",
        "source_url": "https://docs.flipper.net/zero/development/hardware/schematic",
        "repair_relevance": "Needed for display replacement and backlight repair.",
    },
    {
        "file": "schematics/sub-1-ghz-cc1101-schematic.pdf",
        "title": "Sub-1 GHz CC1101 RF Schematic",
        "schematic_type": "full_schematic",
        "description": "Texas Instruments CC1101 sub-GHz transceiver circuit including matching network, antenna switch, and SPI interface to the STM32WB55.",
        "source_type": "official",
        "source_url": "https://docs.flipper.net/zero/development/hardware/schematic",
        "repair_relevance": "Needed for sub-GHz radio troubleshooting and antenna matching issues.",
    },
    {
        "file": "schematics/buttons-schematic.pdf",
        "title": "Buttons Schematic",
        "schematic_type": "full_schematic",
        "description": "Button matrix circuit for the D-pad and back/OK buttons, including ESD protection and debounce components.",
        "source_type": "official",
        "source_url": "https://docs.flipper.net/zero/development/hardware/schematic",
        "repair_relevance": "Useful for button replacement and input troubleshooting.",
    },
    # iButton PCB
    {
        "file": "schematics/power-and-vibro-schematic.pdf",
        "title": "iButton PCB Power & Vibration Motor Schematic",
        "schematic_type": "full_schematic",
        "description": "Power distribution and vibration motor driver circuit on the iButton/NFC daughter board.",
        "source_type": "official",
        "source_url": "https://docs.flipper.net/zero/development/hardware/schematic",
        "repair_relevance": "Needed for vibration motor and daughter board power issues.",
    },
    # NFC/RFID PCB
    {
        "file": "schematics/nfc-blocks.pdf",
        "title": "NFC/RFID PCB Block Diagram",
        "schematic_type": "block_diagram",
        "description": "Block diagram of the NFC/RFID daughter board showing ST25R3916 NFC transceiver and 125 kHz RFID analog front-end.",
        "source_type": "official",
        "source_url": "https://docs.flipper.net/zero/development/hardware/schematic",
        "repair_relevance": "Overview of NFC/RFID subsystem architecture for fault isolation.",
    },
    {
        "file": "schematics/nfc-schematic.pdf",
        "title": "NFC ST25R3916 Schematic",
        "schematic_type": "full_schematic",
        "description": "Detailed schematic of the ST25R3916 NFC transceiver circuit including antenna matching network, SPI interface, and 13.56 MHz oscillator.",
        "source_type": "official",
        "source_url": "https://docs.flipper.net/zero/development/hardware/schematic",
        "repair_relevance": "Critical for NFC antenna tuning and transceiver troubleshooting.",
    },
    {
        "file": "schematics/rfid-schematic.pdf",
        "title": "RFID 125 kHz Schematic",
        "schematic_type": "full_schematic",
        "description": "125 kHz RFID reader/writer analog circuit including coil driver, envelope detector, and comparator for ASK/PSK demodulation.",
        "source_type": "official",
        "source_url": "https://docs.flipper.net/zero/development/hardware/schematic",
        "repair_relevance": "Needed for 125 kHz RFID troubleshooting — involves discrete analog circuitry.",
    },
    # Combined DIY schematic
    {
        "file": "schematics/flipper-zero-diy-combined.pdf",
        "title": "Flipper Zero Complete KiCad Schematic (Community)",
        "schematic_type": "full_schematic",
        "description": "14-page combined KiCad schematic covering all Flipper Zero PCBs, recreated by the community from official schematics. Includes BOM cross-references.",
        "source_type": "community",
        "source_url": "https://github.com/cbwhickstein/Flipper_Zero_DIY",
        "source_notes": "Community KiCad recreation by cbwhickstein, based on official Flipper Devices schematics.",
        "repair_relevance": "Useful as a searchable reference — KiCad-exported PDF allows text search for component values and reference designators.",
        "version": "DIY",
    },
]

# Datasheets to import
DATASHEETS = [
    {
        "file": "datasheets/cc1101.pdf",
        "title": "CC1101 Datasheet — Low-Power Sub-1 GHz RF Transceiver",
        "schematic_type": "datasheet",
        "description": "Texas Instruments CC1101 datasheet. Covers register map, RF performance specs, reference design, and application circuits for 315/433/868/915 MHz operation.",
        "source_type": "official",
        "source_url": "https://www.ti.com/product/CC1101",
        "source_notes": "Official Texas Instruments datasheet.",
        "repair_relevance": "Reference for sub-GHz radio troubleshooting — includes recommended component values for the matching network.",
    },
    {
        "file": "datasheets/stm32wb55rg.pdf",
        "title": "STM32WB55xx/STM32WB35xx Datasheet",
        "schematic_type": "datasheet",
        "description": "STMicroelectronics STM32WB55RG datasheet. Dual-core Cortex-M4 + Cortex-M0+ MCU with BLE 5.4, 802.15.4 radio, 1 MB flash, 256 KB SRAM.",
        "source_type": "official",
        "source_url": "https://www.st.com/en/microcontrollers-microprocessors/stm32wb55rg.html",
        "source_notes": "Official STMicroelectronics datasheet, obtained via Farnell mirror.",
        "repair_relevance": "Pin configuration, electrical characteristics, and absolute maximum ratings needed for MCU-level repair.",
    },
]

# Datasheet URLs to set on existing components
DATASHEET_URLS = {
    ("Texas Instruments", "CC1101RGPR"): "https://www.ti.com/lit/ds/symlink/cc1101.pdf",
    ("STMicroelectronics", "STM32WB55RGV6"): "https://www.st.com/resource/en/datasheet/stm32wb55rg.pdf",
    ("STMicroelectronics", "ST25R3916-AQWT"): "https://www.st.com/resource/en/datasheet/st25r3916.pdf",
}


class Command(BaseCommand):
    help = "Import downloaded Flipper Zero schematics and datasheets into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing Flipper Zero schematics before re-importing.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        admin = User.objects.filter(is_superuser=True).order_by("date_joined").first()
        if not admin:
            self.stderr.write(self.style.ERROR("No admin user found. Run seed_data first."))
            return

        try:
            product = Product.objects.get(manufacturer="Flipper Devices")
        except Product.DoesNotExist:
            self.stderr.write(self.style.ERROR("Flipper Zero product not found. Run seed_data first."))
            return

        base_dir = Path(settings.MEDIA_ROOT) / "downloads" / "flipper-zero"

        if options["flush"]:
            count = product.schematics.count()
            product.schematics.all().delete()
            self.stdout.write(self.style.WARNING(f"Flushed {count} existing Flipper Zero schematics."))

        # Import schematics and datasheets
        all_items = SCHEMATICS + DATASHEETS
        created = 0
        skipped = 0

        for item in all_items:
            file_path = base_dir / item["file"]
            if not file_path.exists():
                self.stderr.write(self.style.WARNING(f"File not found: {file_path}"))
                continue

            # Skip if already exists (match by title)
            if product.schematics.filter(title=item["title"]).exists():
                skipped += 1
                continue

            with open(file_path, "rb") as f:
                schematic = Schematic(
                    product=product,
                    schematic_type=item["schematic_type"],
                    title=item["title"],
                    description=item.get("description", ""),
                    version=item.get("version", ""),
                    source_type=item.get("source_type", "official"),
                    source_url=item.get("source_url", ""),
                    source_notes=item.get("source_notes", ""),
                    repair_relevance=item.get("repair_relevance", ""),
                    is_approved=True,
                    uploaded_by=admin,
                )
                filename = os.path.basename(item["file"])
                schematic.file.save(filename, File(f), save=False)
                schematic.file_size = file_path.stat().st_size
                schematic.file_type = filename.rsplit(".", 1)[-1].lower()
                schematic.save()
                created += 1

        self.stdout.write(f"Schematics: {created} imported, {skipped} already existed.")

        # Update datasheet URLs on components
        updated = 0
        for (mfr, pn), url in DATASHEET_URLS.items():
            count = Component.objects.filter(
                manufacturer=mfr, part_number=pn, datasheet_url=""
            ).update(datasheet_url=url)
            updated += count

        self.stdout.write(f"Component datasheet URLs: {updated} updated.")

        total = product.schematics.filter(is_approved=True).count()
        self.stdout.write(f"Flipper Zero now has {total} schematics.")

        self.stdout.write(self.style.SUCCESS("Import complete."))
