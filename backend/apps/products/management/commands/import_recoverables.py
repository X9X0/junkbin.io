"""
Management command to populate the database with IoT devices that were
orphaned by their manufacturer going out of business, discontinuing cloud
service, or restricting APIs — but which the community has since found a
way to bring back to life (Tasmota, ESPHome, Home Assistant, RATGDO, etc.).

Source: Docs/recoverables.pdf ("Devices that survived because of
open-source communities" + "community fixes" table).

Usage:
    python manage.py import_recoverables          # Add seed data (idempotent)
    python manage.py import_recoverables --flush  # Clear this seed data first, then re-add
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.products.models import Product

User = get_user_model()

# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

PRODUCTS = [
    {
        "manufacturer": "Wink",
        "model_number": "Wink Hub",
        "category": "smart_home",
        "year_manufactured": 2014,
        "description": "Cloud-connected smart home hub bridging Zigbee, Z-Wave, Lutron Clear Connect, and Kidde. Wink's cloud service nearly collapsed in 2020 and introduced a mandatory monthly subscription, leaving hubs unusable for anyone who didn't pay.",
        "teardown_notes": "Recovery difficulty: high, but the most actively rescued hub in the community. Local API has been reverse-engineered, rooted/modified firmware exists, and Home Assistant integrations restore local control with no Wink cloud or subscription required.",
    },
    {
        "manufacturer": "Lowe's",
        "model_number": "Iris Smart Hub",
        "category": "smart_home",
        "year_manufactured": 2014,
        "description": "Zigbee/Z-Wave home automation hub for Lowe's Iris platform. Lowe's discontinued Iris in 2019, shutting down the cloud service the hub depended on.",
        "teardown_notes": "Recovery difficulty: easy. The hub itself isn't needed for continued use — replace it with a modern Zigbee/Z-Wave coordinator and pair the surviving Iris peripherals to Home Assistant or OpenHAB. Nearly all sensors and plugs can be reused this way.",
    },
    {
        "manufacturer": "Lowe's",
        "model_number": "Iris Contact Sensor",
        "category": "smart_home",
        "year_manufactured": 2014,
        "description": "Zigbee door/window contact sensor sold as part of the Iris platform. Left orphaned when Lowe's shut down Iris in 2019.",
        "teardown_notes": "Recovery difficulty: easy. Standard Zigbee HA (Home Automation) profile device — pairs directly to any modern Zigbee coordinator (e.g. Texas Instruments CC2652 or Silicon Labs EFR32 based) using Zigbee2MQTT or ZHA in Home Assistant.",
    },
    {
        "manufacturer": "Lowe's",
        "model_number": "Iris Motion Sensor",
        "category": "smart_home",
        "year_manufactured": 2014,
        "description": "Zigbee PIR motion sensor sold as part of the Iris platform. Left orphaned when Lowe's shut down Iris in 2019.",
        "teardown_notes": "Recovery difficulty: easy. Standard Zigbee HA profile device — pairs directly to any modern Zigbee coordinator using Zigbee2MQTT or ZHA in Home Assistant, same as the Iris contact sensor.",
    },
    {
        "manufacturer": "Insteon",
        "model_number": "Insteon Hub",
        "category": "smart_home",
        "year_manufactured": 2014,
        "description": "Hub for Insteon's dual-band (RF + powerline) home automation ecosystem. Insteon abruptly shut down in 2022 with no warning, leaving hubs unable to reach the cloud.",
        "teardown_notes": "Recovery difficulty: moderate. Home Assistant's Insteon integration, Universal Devices ISY controllers/firmware, and community hub-API reverse engineering restore local automation. When Insteon later resumed operations, many users kept their local-only setup instead of switching back.",
    },
    {
        "manufacturer": "Chamberlain Group",
        "model_number": "MyQ Garage Door Opener",
        "category": "other",
        "subcategory": "Garage Door Opener",
        "year_manufactured": 2017,
        "description": "WiFi garage door opener/controller. Chamberlain restricted third-party API access, breaking existing Home Assistant, IFTTT, and SmartThings integrations for anyone who didn't pay for official partner access.",
        "teardown_notes": "Recovery difficulty: moderate — one of the best examples of community innovation. RATGDO is an ESP32-based replacement interface that talks directly to the opener hardware; combined with ESPHome/MQTT and Home Assistant, it bypasses Chamberlain's cloud entirely and is often faster and more reliable than the official app.",
    },
    {
        "manufacturer": "Icontrol Networks",
        "model_number": "Piper NV",
        "category": "security_cam",
        "year_manufactured": 2015,
        "description": "All-in-one home security camera with built-in siren, Z-Wave hub, and environmental sensors. Icontrol Networks ended cloud support after an acquisition, disabling remote monitoring and access.",
        "teardown_notes": "Recovery difficulty: high. Community projects extract the local RTSP video stream directly from the camera, restoring local viewing/recording (e.g. via Frigate or Blue Iris) without the original cloud service. The built-in Z-Wave hub function is not part of this fix.",
    },
    {
        "manufacturer": "Canary",
        "model_number": "Canary",
        "category": "security_cam",
        "year_manufactured": 2015,
        "description": "All-in-one home security camera with AI-based activity detection. Canary survived as a company but removed previously advertised features (like unlimited free cloud recording), prompting user lawsuits — a cautionary example of cloud dependency even without bankruptcy.",
        "teardown_notes": "Recovery difficulty: high. Community-driven local video streaming reverse engineering bypasses the increasingly limited official app/cloud tier.",
    },
    {
        "manufacturer": "Belkin",
        "model_number": "WeMo Switch",
        "category": "smart_home",
        "year_manufactured": 2011,
        "description": "WiFi smart plug/switch. Cloud and companion app support have aged and been scaled back over time, though the device was never formally discontinued.",
        "teardown_notes": "Recovery difficulty: easy — one of the simplest devices to rescue. WeMo exposes a local UPnP control API; Home Assistant's WeMo integration controls it entirely locally with no cloud dependency.",
    },
    {
        "manufacturer": "ITEAD",
        "model_number": "Sonoff Basic R2",
        "category": "smart_home",
        "year_manufactured": 2018,
        "description": "Inexpensive WiFi relay switch built on an ESP8266/ESP8285. Ships with optional (but default) Tuya-style cloud dependency for remote control.",
        "teardown_notes": "Recovery difficulty: moderate. Reflash with Tasmota, ESPHome, or OpenBeken for fully local control via MQTT/Home Assistant — no cloud required. Representative of a huge rescued-device family: thousands of similar ESP8266/ESP8285-based devices from Tuya, Gosund, Treatlife, BlitzWolf, and Teckin can be rescued the same way.",
    },
    {
        "manufacturer": "Shelly",
        "model_number": "Shelly 1",
        "category": "smart_home",
        "year_manufactured": 2017,
        "description": "DIN-rail/inline WiFi relay module. Shelly devices were never abandoned by their manufacturer, but are widely cited as the model example for 'local-first' IoT design.",
        "teardown_notes": "Recovery difficulty: n/a (not orphaned) — included for reference. Community has built ESPHome firmware, MQTT integrations, Home Assistant firmware, local scripting, and Matter bridges for Shelly hardware, often cited as the gold standard other rescued devices are compared against.",
    },
]


class Command(BaseCommand):
    help = "Populate the database with orphaned-but-hackable IoT devices (community fixes for defunct-cloud hardware)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing entries from this seed set before inserting (matches by manufacturer/model).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        admin = self._get_or_create_admin()
        self.stdout.write(f"Using admin user: {admin.username}")

        if options["flush"]:
            self._flush()

        self._create_products(admin)

        self.stdout.write(self.style.SUCCESS("Recoverable IoT device data loaded successfully."))

    # ------------------------------------------------------------------

    def _get_or_create_admin(self):
        admin = User.objects.filter(is_superuser=True).order_by("date_joined").first()
        if admin:
            return admin
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@junkbin.local",
            password="admin",
        )
        admin.email_verified = True
        admin.save(update_fields=["email_verified"])
        self.stdout.write(self.style.WARNING("Created default admin user (admin / admin)."))
        return admin

    def _flush(self):
        keys = [(p["manufacturer"], p["model_number"]) for p in PRODUCTS]
        q = Product.objects.none()
        for mfr, model in keys:
            q = q | Product.objects.filter(manufacturer=mfr, model_number=model)
        count = q.count()
        q.delete()
        self.stdout.write(self.style.WARNING(f"Flushed {count} products."))

    def _create_products(self, admin):
        created = 0
        for data in PRODUCTS:
            obj, is_new = Product.objects.get_or_create(
                manufacturer=data["manufacturer"],
                model_number=data["model_number"],
                defaults={
                    "category": data["category"],
                    "subcategory": data.get("subcategory", ""),
                    "year_manufactured": data.get("year_manufactured"),
                    "description": data.get("description", ""),
                    "teardown_notes": data.get("teardown_notes", ""),
                    "is_approved": True,
                    "created_by": admin,
                },
            )
            if is_new:
                created += 1
        self.stdout.write(f"Products: {created} created, {len(PRODUCTS) - created} already existed.")
