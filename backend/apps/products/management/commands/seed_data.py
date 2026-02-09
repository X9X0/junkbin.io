"""
Management command to populate the database with realistic electronics teardown seed data.

Usage:
    python manage.py seed_data          # Add seed data (idempotent)
    python manage.py seed_data --flush  # Clear seed data first, then re-add
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.products.models import Product
from apps.components.models import Component, ProductComponent

User = get_user_model()

# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

PRODUCTS = [
    {
        "manufacturer": "TP-Link",
        "model_number": "Archer AX73",
        "category": "router",
        "year_manufactured": 2022,
        "fcc_id": "TE7AX73",
        "description": "AX5400 dual-band WiFi 6 router with 6 high-gain antennas and 1.5 GHz triple-core CPU.",
        "teardown_notes": "Four Phillips screws under rubber feet. Clips along the perimeter require a spudger. Single PCB with integrated heatsink.",
    },
    {
        "manufacturer": "Raspberry Pi",
        "model_number": "4 Model B",
        "category": "sbc",
        "year_manufactured": 2019,
        "fcc_id": "2ABCB-RPI4B",
        "description": "Quad-core Cortex-A72 single-board computer with up to 8 GB RAM, dual micro-HDMI, USB 3.0, and Gigabit Ethernet.",
        "teardown_notes": "No screws — board is open. Heatsink or case must be removed first. Key ICs on top side only.",
    },
    {
        "manufacturer": "Sony",
        "model_number": "DualSense CFI-ZCT1G",
        "category": "controller",
        "year_manufactured": 2020,
        "description": "PlayStation 5 wireless controller with haptic feedback and adaptive triggers.",
        "teardown_notes": "Remove black shell trim, four Phillips screws underneath. Battery connected via JST connector. Trigger mechanisms are spring-loaded — reassemble carefully.",
    },
    {
        "manufacturer": "Apple",
        "model_number": "AirPods Pro 2nd Gen MQD83",
        "category": "headphones",
        "year_manufactured": 2022,
        "fcc_id": "BCG-E4091A",
        "description": "Active noise-cancelling true wireless earbuds with H2 chip and USB-C charging case.",
        "teardown_notes": "Destructive teardown — glued shut. Heat required to soften adhesive on case. Earbuds themselves are essentially non-repairable.",
    },
    {
        "manufacturer": "Samsung",
        "model_number": "990 Pro 2TB MZ-V9P2T0",
        "category": "ssd",
        "year_manufactured": 2022,
        "description": "PCIe 4.0 NVMe M.2 SSD with V-NAND and up to 7,450 MB/s sequential read.",
        "teardown_notes": "Peel label to expose controller and NAND packages. Single-sided layout on 2280 form factor.",
    },
    {
        "manufacturer": "Ubiquiti",
        "model_number": "UniFi U6-Pro",
        "category": "access_point",
        "year_manufactured": 2022,
        "fcc_id": "SWX-U6PRO",
        "description": "WiFi 6 dual-band access point with 4x4 MU-MIMO, PoE powered, ceiling-mount design.",
        "teardown_notes": "Twist-lock mount releases the unit. Three T10 Torx screws hold the back cover. RF shield cans are soldered — need hot air to remove.",
    },
    {
        "manufacturer": "Valve",
        "model_number": "Steam Deck OLED 1030",
        "category": "handheld",
        "year_manufactured": 2023,
        "fcc_id": "2AFGB1030",
        "description": "Handheld gaming PC with custom AMD APU, 7.4-inch OLED display, and 50 Wh battery.",
        "teardown_notes": "Eight Phillips screws on the back. Careful with ribbon cables for triggers and trackpads. Battery is held with adhesive pull-tabs. M.2 2230 SSD is user-replaceable.",
    },
    {
        "manufacturer": "Framework",
        "model_number": "Laptop 16 FRANMZ16",
        "category": "laptop",
        "year_manufactured": 2024,
        "description": "Modular laptop with AMD Ryzen 7840HS, user-swappable GPU module, expansion card bays, and tool-less access.",
        "teardown_notes": "Five captive Phillips screws on the bottom midplate. Input modules lift out with no tools. RAM and SSD accessible immediately. GPU module has a dedicated connector.",
    },
    {
        "manufacturer": "Google",
        "model_number": "Nest Thermostat G4CVZ",
        "category": "thermostat",
        "year_manufactured": 2020,
        "fcc_id": "A4RG4CVZ",
        "description": "Smart thermostat with mirror glass display, Soli radar sensor, and HVAC control via WiFi.",
        "teardown_notes": "Display pulls off magnetically. Two Phillips screws to remove the base. Internal battery is rechargeable Li-ion, charged from the HVAC C-wire.",
    },
    {
        "manufacturer": "Flipper Devices",
        "model_number": "Flipper Zero FZ.1",
        "category": "other",
        "year_manufactured": 2022,
        "fcc_id": "2A2V6-FZ",
        "description": "Multi-tool device for pentesters and hardware enthusiasts. STM32WB55 dual-core MCU, CC1101 sub-GHz transceiver (315/433/868/915 MHz), ST25R3916 NFC (13.56 MHz), IR transceiver, iButton/1-Wire, 128x64 ST7567 LCD, 2100 mAh LiPo, USB-C (USB 2.0), and 18-pin GPIO header with 3.3V/5V/UART/SPI/I2C/USB.",
        "teardown_notes": "Six Phillips screws on the back. Two-piece plastic shell. Main PCB has STM32WB55 at center, CC1101 sub-GHz section near left antenna pad, ST25R3916 NFC section near top antenna loop. Battery is a 2100 mAh LiPo pouch cell connected via JST. LCD and buttons connect via FPC. GPIO header is directly soldered to main PCB.",
    },
]

COMPONENTS = [
    # --- SoCs and main processors ---
    {
        "manufacturer": "MediaTek",
        "part_number": "MT7986BV",
        "component_type": "ic",
        "package_type": "BGA-489",
        "description": "Filogic 830 WiFi 6E/6 SoC with dual-core Arm Cortex-A53 at 2 GHz.",
        "typical_function": "WiFi 6 SoC / main processor",
        "specifications": {"cores": 2, "architecture": "Cortex-A53", "frequency_ghz": 2.0, "wifi": "802.11ax"},
    },
    {
        "manufacturer": "Broadcom",
        "part_number": "BCM2711ZPKFSB06",
        "component_type": "ic",
        "package_type": "LFBGA-292",
        "description": "Quad-core Cortex-A72 SoC at 1.5 GHz, used in Raspberry Pi 4.",
        "typical_function": "Application processor / SoC",
        "specifications": {"cores": 4, "architecture": "Cortex-A72", "frequency_ghz": 1.5},
    },
    {
        "manufacturer": "AMD",
        "part_number": "100-000000680",
        "component_type": "ic",
        "package_type": "FP7r2",
        "description": "Custom AMD Van Gogh APU — Zen 2 CPU + RDNA 2 GPU, designed for Steam Deck.",
        "typical_function": "APU / main processor",
        "specifications": {"cpu_cores": 4, "gpu_cus": 8, "architecture": "Zen 2 + RDNA 2"},
    },
    {
        "manufacturer": "AMD",
        "part_number": "100-000000902",
        "component_type": "ic",
        "package_type": "FP7/FP8",
        "description": "Ryzen 7 7840HS — Zen 4 CPU with RDNA 3 integrated graphics.",
        "typical_function": "Laptop APU",
        "specifications": {"cpu_cores": 8, "gpu_cus": 12, "architecture": "Zen 4 + RDNA 3"},
    },
    {
        "manufacturer": "Apple",
        "part_number": "H2",
        "component_type": "ic",
        "package_type": "SiP",
        "description": "Apple H2 chip — ANC processor with Bluetooth 5.3 and adaptive transparency.",
        "typical_function": "Audio processor / BLE SoC",
    },
    {
        "manufacturer": "Samsung",
        "part_number": "S4LR032",
        "component_type": "ic",
        "package_type": "BGA",
        "description": "Pascal NVMe SSD controller — 8-channel, PCIe 4.0 x4.",
        "typical_function": "SSD controller",
        "specifications": {"interface": "PCIe 4.0 x4", "channels": 8, "protocol": "NVMe 2.0"},
    },
    {
        "manufacturer": "Qualcomm",
        "part_number": "QCA8081",
        "component_type": "ic",
        "package_type": "QFN-56",
        "description": "Single-port 2.5G Ethernet PHY transceiver.",
        "typical_function": "Ethernet PHY",
        "specifications": {"speed": "2.5 Gbps", "interface": "SGMII/RGMII"},
    },
    # --- Microcontrollers ---
    {
        "manufacturer": "STMicroelectronics",
        "part_number": "STM32WB55RGV6",
        "component_type": "mcu",
        "package_type": "VFQFPN-68",
        "description": "Dual-core MCU — Cortex-M4 at 64 MHz (app processor) + Cortex-M0+ at 32 MHz (BLE 5.4/802.15.4 radio stack). 1 MB flash, 256 KB SRAM.",
        "typical_function": "Wireless microcontroller (BLE 5.4 / Zigbee / Thread)",
        "specifications": {"flash_kb": 1024, "ram_kb": 256, "frequency_mhz": 64},
    },
    {
        "manufacturer": "Nordic Semiconductor",
        "part_number": "nRF52840-QIAA",
        "component_type": "mcu",
        "package_type": "QFN-73",
        "description": "Multiprotocol SoC with Cortex-M4F, BLE 5.0, 802.15.4, and USB.",
        "typical_function": "BLE/NFC microcontroller",
        "specifications": {"flash_kb": 1024, "ram_kb": 256, "frequency_mhz": 64},
    },
    {
        "manufacturer": "Renesas",
        "part_number": "R5F51403ADFM",
        "component_type": "mcu",
        "package_type": "LQFP-48",
        "description": "RX140 series MCU — Cortex-equivalent RXv2 core at 48 MHz with capacitive touch.",
        "typical_function": "Touch-sense controller MCU",
        "specifications": {"flash_kb": 256, "ram_kb": 32, "frequency_mhz": 48},
    },
    # --- Memory ---
    {
        "manufacturer": "SK hynix",
        "part_number": "H5ANAG8NDJR-XNC",
        "component_type": "ic",
        "package_type": "FBGA-96",
        "description": "4 GB DDR4 SDRAM, single die, 3200 Mbps.",
        "typical_function": "System memory (DDR4)",
        "specifications": {"capacity_gb": 4, "type": "DDR4", "speed_mbps": 3200},
    },
    {
        "manufacturer": "Micron",
        "part_number": "MT62F1G32D4DR-031",
        "component_type": "ic",
        "package_type": "FBGA-200",
        "description": "4 GB LPDDR5 SDRAM, 6400 Mbps, low-power for mobile/handheld.",
        "typical_function": "System memory (LPDDR5)",
        "specifications": {"capacity_gb": 4, "type": "LPDDR5", "speed_mbps": 6400},
    },
    {
        "manufacturer": "Samsung",
        "part_number": "K9DLGD8J0A-DCB0",
        "component_type": "ic",
        "package_type": "TBGA-316",
        "description": "1 TB V-NAND TLC flash package, 176-layer, for NVMe SSDs.",
        "typical_function": "NAND flash storage",
        "specifications": {"capacity_tb": 1, "layers": 176, "type": "V-NAND TLC"},
    },
    # --- Power management ---
    {
        "manufacturer": "Texas Instruments",
        "part_number": "TPS65988DH",
        "component_type": "ic",
        "package_type": "BGA-96",
        "description": "USB Type-C and USB PD controller with integrated power paths.",
        "typical_function": "USB-C PD controller",
        "specifications": {"pd_version": "3.1", "max_power_w": 100},
    },
    {
        "manufacturer": "Monolithic Power Systems",
        "part_number": "MP8759GD",
        "component_type": "regulator",
        "package_type": "QFN-20",
        "description": "16V, 12A synchronous step-down converter, 500 kHz.",
        "typical_function": "Core voltage regulator",
        "specifications": {"vin_max_v": 16, "iout_a": 12, "frequency_khz": 500},
    },
    {
        "manufacturer": "Texas Instruments",
        "part_number": "TPS51397A",
        "component_type": "regulator",
        "package_type": "VQFN-22",
        "description": "D-CAP3 step-down controller for IMVP9/VR14 CPU rails.",
        "typical_function": "CPU voltage regulator",
        "specifications": {"phases": 1, "vin_max_v": 20, "output_a": 40},
    },
    {
        "manufacturer": "Richtek",
        "part_number": "RT6190AGQ",
        "component_type": "regulator",
        "package_type": "WQFN-20",
        "description": "4-switch buck-boost converter, 36V input, 10A output.",
        "typical_function": "Buck-boost regulator (battery charger path)",
        "specifications": {"topology": "buck-boost", "vin_max_v": 36, "iout_a": 10},
    },
    # --- RF front-end ---
    {
        "manufacturer": "Skyworks",
        "part_number": "SKY85755-11",
        "component_type": "rf_module",
        "package_type": "MCM-24",
        "description": "5 GHz WiFi 6 front-end module with PA, LNA, and T/R switch.",
        "typical_function": "5 GHz WiFi FEM",
        "specifications": {"frequency_ghz": 5, "gain_db": 14, "pout_dbm": 21},
    },
    {
        "manufacturer": "Qorvo",
        "part_number": "QPF4528",
        "component_type": "rf_module",
        "package_type": "QFN-16",
        "description": "2.4 GHz WiFi 6 front-end module with integrated PA and LNA.",
        "typical_function": "2.4 GHz WiFi FEM",
        "specifications": {"frequency_ghz": 2.4, "pout_dbm": 23},
    },
    # --- Passives (notable ones) ---
    {
        "manufacturer": "Murata",
        "part_number": "GRM188R71H104KA93D",
        "component_type": "capacitor",
        "package_type": "0603",
        "description": "100 nF MLCC, X7R, 50V, general-purpose decoupling.",
        "typical_function": "Bypass / decoupling capacitor",
        "specifications": {"capacitance_nf": 100, "voltage_v": 50, "dielectric": "X7R"},
    },
    {
        "manufacturer": "TDK",
        "part_number": "VLF3012AT-100MR87",
        "component_type": "inductor",
        "package_type": "3012",
        "description": "10 µH power inductor, 0.87 A saturation, for DC-DC converters.",
        "typical_function": "Power inductor",
        "specifications": {"inductance_uh": 10, "isat_a": 0.87, "dcr_mohm": 280},
    },
    {
        "manufacturer": "Murata",
        "part_number": "BLM18PG221SH1D",
        "component_type": "ferrite",
        "package_type": "0603",
        "description": "220 ohm ferrite bead at 100 MHz, 1.5 A rated, for EMI filtering.",
        "typical_function": "EMI filter bead",
        "specifications": {"impedance_ohm": 220, "frequency_mhz": 100, "irated_a": 1.5},
    },
    {
        "manufacturer": "Yageo",
        "part_number": "RC0402FR-0710KL",
        "component_type": "resistor",
        "package_type": "0402",
        "description": "10 kΩ thick-film resistor, 1%, 1/16 W.",
        "typical_function": "Pull-up / bias resistor",
        "specifications": {"resistance_ohm": 10000, "tolerance_pct": 1, "power_w": 0.0625},
    },
    # --- Connectors ---
    {
        "manufacturer": "JAE Electronics",
        "part_number": "DX07S024JJ3R1500",
        "component_type": "connector",
        "package_type": "SMD",
        "description": "USB Type-C receptacle, 24-pin, mid-mount, for USB 3.2 Gen 2.",
        "typical_function": "USB-C port",
        "specifications": {"pins": 24, "standard": "USB 3.2 Gen 2"},
    },
    # --- Sensors / Misc ICs ---
    {
        "manufacturer": "Bosch",
        "part_number": "BMI270",
        "component_type": "sensor",
        "package_type": "LGA-14",
        "description": "6-axis IMU — accelerometer + gyroscope, ultra-low power.",
        "typical_function": "Motion sensor / IMU",
        "specifications": {"axes": 6, "accel_range_g": 16, "gyro_range_dps": 2000},
    },
    {
        "manufacturer": "Texas Instruments",
        "part_number": "BQ25896",
        "component_type": "ic",
        "package_type": "VQFN-24",
        "description": "I2C-controlled 3A single-cell battery charger with NVDC power path.",
        "typical_function": "Battery charge controller",
        "specifications": {"vin_max_v": 14, "charge_current_a": 3, "cells": 1},
    },
    {
        "manufacturer": "Broadcom",
        "part_number": "BCM54213PE",
        "component_type": "ic",
        "package_type": "QFN-48",
        "description": "Gigabit Ethernet PHY transceiver with integrated 10/100/1000BASE-T.",
        "typical_function": "Gigabit Ethernet PHY",
        "specifications": {"speed": "1 Gbps", "interface": "RGMII"},
    },
    {
        "manufacturer": "Cypress",
        "part_number": "CYW43455",
        "component_type": "rf_module",
        "package_type": "WLBGA-95",
        "description": "Dual-band 802.11ac WiFi + Bluetooth 5.0 combo chip.",
        "typical_function": "WiFi/BT combo",
        "specifications": {"wifi": "802.11ac", "bluetooth": "5.0", "bands": "2.4/5 GHz"},
    },
    {
        "manufacturer": "Espressif",
        "part_number": "ESP32-S3R8",
        "component_type": "mcu",
        "package_type": "QFN-56",
        "description": "Dual-core Xtensa LX7 MCU with WiFi 4 + BLE 5, 8 MB PSRAM.",
        "typical_function": "WiFi/BLE microcontroller",
        "specifications": {"cores": 2, "frequency_mhz": 240, "psram_mb": 8},
    },
    # --- Flipper Zero specific ---
    {
        "manufacturer": "Texas Instruments",
        "part_number": "CC1101RGPR",
        "component_type": "rf_module",
        "package_type": "QFN-20",
        "description": "Low-power sub-1 GHz RF transceiver supporting 300-348 MHz, 387-464 MHz, and 779-928 MHz bands. Max +12 dBm output, OOK/2-FSK/4-FSK/MSK modulation. Used in Flipper Zero for sub-GHz communication.",
        "typical_function": "Sub-1 GHz RF transceiver",
        "specifications": {"frequency_ghz": 0.915, "pout_dbm": 12, "modulation": "OOK/FSK/MSK", "sensitivity_dbm": -116},
    },
    {
        "manufacturer": "STMicroelectronics",
        "part_number": "ST25R3916-AQWT",
        "component_type": "ic",
        "package_type": "UFQFPN-32",
        "description": "High-performance NFC universal device (NFCD) with integrated analog front-end. Supports NFC-A/B/F/V, ISO 14443A/B, ISO 15693, FeliCa, and EMVCo. 1.6 W antenna driver output. Used in Flipper Zero for NFC/RFID operations at 13.56 MHz.",
        "typical_function": "NFC/RFID transceiver",
        "specifications": {"frequency_mhz": 13.56, "protocols": "NFC-A/B/F/V, ISO 14443, ISO 15693", "tx_power_w": 1.6},
    },
    {
        "manufacturer": "Sitronix",
        "part_number": "ST7567",
        "component_type": "display",
        "package_type": "COG",
        "description": "65x132 dot-matrix LCD controller/driver with SPI interface, used to drive the Flipper Zero 128x64 monochrome LCD. 1/65 duty, 1/9 bias.",
        "typical_function": "LCD controller/driver",
        "specifications": {"resolution": "128x64", "interface": "SPI", "voltage_v": 3.3},
    },
]

# (product index, component index, ref_designator, quantity, location_description, board_name, notes)
PRODUCT_COMPONENT_LINKS = [
    # TP-Link Archer AX73
    (0, 0, "U1", 1, "Center of PCB under heatsink", "Main Board", "Primary SoC — MediaTek Filogic 830"),
    (0, 10, "U2", 2, "Adjacent to SoC", "Main Board", "2x 4 GB DDR4 = 8 GB total system RAM"),
    (0, 6, "U3", 1, "Near RJ45 jack cluster", "Main Board", "2.5G WAN port PHY"),
    (0, 17, "U11", 3, "Near antenna connectors, 5 GHz chain", "Main Board", "5 GHz WiFi 6 front-end modules (3 chains)"),
    (0, 18, "U14", 2, "Near antenna connectors, 2.4 GHz chain", "Main Board", "2.4 GHz WiFi 6 front-end modules"),
    (0, 19, "C15", 40, "Distributed across PCB", "Main Board", ""),
    (0, 21, "FB1", 8, "Power input section", "Main Board", "EMI filtering on power rails"),

    # Raspberry Pi 4 Model B
    (1, 1, "U1", 1, "Center of board (top)", "Main Board", "BCM2711 quad-core SoC"),
    (1, 10, "U2", 1, "Top, adjacent to SoC", "Main Board", "4 GB DDR4 SDRAM (PoP or discrete depending on SKU)"),
    (1, 26, "U3", 1, "Top, near USB ports", "Main Board", "Gigabit Ethernet PHY"),
    (1, 27, "U4", 1, "Top, near GPIO header", "Main Board", "WiFi/BT combo module"),
    (1, 23, "J1", 1, "Edge, USB-C power input", "Main Board", "USB-C power connector"),
    (1, 19, "C1", 25, "Distributed", "Main Board", "Decoupling capacitors for SoC and memory"),

    # Sony DualSense
    (2, 7, "U1", 1, "Center of main PCB", "Main Board", "Wireless MCU — handles BLE and proprietary 2.4 GHz"),
    (2, 24, "U5", 1, "Near center of PCB", "Main Board", "6-axis IMU for motion controls"),
    (2, 9, "U6", 1, "Near touchpad connector", "Main Board", "Touch controller MCU"),
    (2, 19, "C3", 18, "Around MCU and RF section", "Main Board", ""),
    (2, 22, "R7", 15, "Distributed", "Main Board", "Bias and pull-up resistors"),
    (2, 23, "J2", 1, "Bottom edge of controller", "Main Board", "USB-C charge/data port"),

    # Apple AirPods Pro 2
    (3, 4, "U1", 1, "Inside earbud (potted)", "Earbud PCB", "H2 chip — audio, ANC, Bluetooth"),
    (3, 19, "C1", 10, "Around H2", "Earbud PCB", ""),

    # Samsung 990 Pro 2TB
    (4, 5, "U1", 1, "Center of M.2 PCB", "Main Board", "Pascal NVMe controller"),
    (4, 12, "U2", 2, "Flanking the controller", "Main Board", "1 TB V-NAND packages (2x = 2 TB)"),
    (4, 11, "U5", 1, "Near controller", "Main Board", "LPDDR4 cache buffer"),
    (4, 19, "C8", 12, "Near controller power pins", "Main Board", "Decoupling for controller power rails"),
    (4, 22, "R1", 6, "Near edge connector", "Main Board", "Impedance-matching resistors for PCIe lanes"),

    # Ubiquiti UniFi U6-Pro
    (5, 0, "U1", 1, "Under main RF shield", "Main Board", "MediaTek SoC — same family as AX73"),
    (5, 10, "U2", 1, "Adjacent to SoC", "Main Board", "DDR4 system memory"),
    (5, 17, "U10", 4, "Near each antenna feed", "Main Board", "5 GHz FEM for 4x4 MIMO"),
    (5, 18, "U14", 2, "Near 2.4 GHz antenna feeds", "Main Board", "2.4 GHz WiFi FEM"),
    (5, 19, "C20", 30, "Distributed", "Main Board", ""),
    (5, 21, "FB5", 6, "Power section near PoE input", "Main Board", "EMI filter beads on PoE rail"),
    (5, 20, "L3", 4, "Buck converter output stages", "Main Board", "Power inductors for voltage regulators"),

    # Steam Deck OLED
    (6, 2, "U1", 1, "Center of main board, under heatsink/copper", "Main Board", "Custom AMD Van Gogh APU"),
    (6, 11, "U2", 2, "Either side of APU", "Main Board", "LPDDR5 memory (2x 4 GB = 8 GB)"),
    (6, 16, "U10", 1, "Near battery connector", "Main Board", "Buck-boost for battery power path"),
    (6, 25, "U12", 1, "Near USB-C port", "Main Board", "Battery charge management"),
    (6, 24, "U15", 1, "Near left stick", "Main Board", "Motion sensor IMU"),
    (6, 13, "U20", 1, "Near USB-C port", "Main Board", "USB PD controller"),
    (6, 23, "J1", 1, "Top edge, near vent", "Main Board", "USB-C port"),
    (6, 19, "C30", 35, "Distributed across main board", "Main Board", ""),

    # Framework Laptop 16
    (7, 3, "U1", 1, "Under heatsink/heatpipe assembly", "Mainboard", "AMD Ryzen 7 7840HS APU"),
    (7, 15, "U5", 1, "Near CPU VRM cluster", "Mainboard", "CPU core voltage regulator controller"),
    (7, 14, "U6", 1, "Near SSD slot", "Mainboard", "MPS step-down for SSD/IO rail"),
    (7, 13, "U10", 2, "Near each USB-C port", "Mainboard", "USB-C PD controllers (2 ports)"),
    (7, 23, "J1", 2, "Left and right edge card slots", "Mainboard", "USB-C expansion card receptacles"),
    (7, 19, "C50", 50, "Distributed across mainboard", "Mainboard", ""),
    (7, 22, "R20", 20, "Around CPU, memory, and PD ICs", "Mainboard", ""),
    (7, 20, "L5", 6, "VRM output stages", "Mainboard", "Power inductors for CPU and GPU rails"),

    # Google Nest Thermostat
    (8, 28, "U1", 1, "Center of display PCB", "Display Board", "ESP32-S3 — main app processor with WiFi/BLE"),
    (8, 9, "U3", 1, "Near display connector", "Display Board", "Touch controller for capacitive glass"),
    (8, 19, "C5", 15, "Around ESP32 and power section", "Display Board", ""),
    (8, 22, "R10", 10, "Distributed", "Display Board", ""),

    # Flipper Zero
    (9, 7, "U1", 1, "Center of main PCB", "Main Board", "STM32WB55 — dual-core MCU (Cortex-M4 + Cortex-M0+), main app processor + BLE 5.4 radio"),
    (9, 29, "U2", 1, "Near left sub-GHz antenna pad", "Main Board", "CC1101 — sub-1 GHz transceiver for 315/433/868/915 MHz protocols"),
    (9, 30, "U3", 1, "Near top NFC antenna loop", "Main Board", "ST25R3916 — NFC/RFID analog front-end for 13.56 MHz (ISO 14443, ISO 15693, FeliCa)"),
    (9, 31, "U4", 1, "Near LCD FPC connector", "Main Board", "ST7567 — 128x64 monochrome LCD controller/driver (SPI)"),
    (9, 19, "C8", 20, "Distributed across board", "Main Board", "Decoupling capacitors"),
    (9, 22, "R5", 12, "Distributed", "Main Board", "Pull-ups and bias network"),
    (9, 23, "J1", 1, "Bottom edge", "Main Board", "USB-C port for charging and USB 2.0 data (12 Mbps)"),
    (9, 25, "U8", 1, "Near USB-C", "Main Board", "Battery charger IC (2100 mAh LiPo)"),
]


class Command(BaseCommand):
    help = "Populate the database with realistic electronics teardown seed data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing seed data before inserting (matches by manufacturer/model).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        admin = self._get_or_create_admin()
        self.stdout.write(f"Using admin user: {admin.username}")

        if options["flush"]:
            self._flush(admin)

        products = self._create_products(admin)
        components = self._create_components(admin)
        self._create_product_components(admin, products, components)
        self._update_counts(products, components)

        self.stdout.write(self.style.SUCCESS("Seed data loaded successfully."))

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
        self.stdout.write(self.style.WARNING("Created default admin user (admin / admin)."))
        return admin

    def _flush(self, admin):
        # Delete ProductComponents first (CASCADE would handle it, but be explicit)
        pc_count = ProductComponent.objects.filter(created_by=admin).count()
        ProductComponent.objects.filter(created_by=admin).delete()

        # Delete products matching our seed set
        p_keys = [(p["manufacturer"], p["model_number"]) for p in PRODUCTS]
        p_q = Product.objects.none()
        for mfr, model in p_keys:
            p_q = p_q | Product.objects.filter(manufacturer=mfr, model_number=model)
        p_count = p_q.count()
        p_q.delete()

        # Delete components matching our seed set
        c_keys = [(c["manufacturer"], c["part_number"]) for c in COMPONENTS]
        c_q = Component.objects.none()
        for mfr, pn in c_keys:
            c_q = c_q | Component.objects.filter(manufacturer=mfr, part_number=pn)
        c_count = c_q.count()
        c_q.delete()

        self.stdout.write(
            self.style.WARNING(
                f"Flushed {p_count} products, {c_count} components, {pc_count} product-components."
            )
        )

    def _create_products(self, admin):
        products = []
        created = 0
        for data in PRODUCTS:
            obj, is_new = Product.objects.get_or_create(
                manufacturer=data["manufacturer"],
                model_number=data["model_number"],
                defaults={
                    "category": data["category"],
                    "year_manufactured": data.get("year_manufactured"),
                    "fcc_id": data.get("fcc_id", ""),
                    "description": data.get("description", ""),
                    "teardown_notes": data.get("teardown_notes", ""),
                    "is_approved": True,
                    "created_by": admin,
                },
            )
            if is_new:
                created += 1
            products.append(obj)
        self.stdout.write(f"Products: {created} created, {len(products) - created} already existed.")
        return products

    def _create_components(self, admin):
        components = []
        created = 0
        for data in COMPONENTS:
            obj, is_new = Component.objects.get_or_create(
                manufacturer=data["manufacturer"],
                part_number=data["part_number"],
                defaults={
                    "component_type": data["component_type"],
                    "package_type": data.get("package_type", ""),
                    "description": data.get("description", ""),
                    "typical_function": data.get("typical_function", ""),
                    "specifications": data.get("specifications", {}),
                    "is_verified": True,
                    "created_by": admin,
                },
            )
            if is_new:
                created += 1
            components.append(obj)
        self.stdout.write(f"Components: {created} created, {len(components) - created} already existed.")
        return components

    def _create_product_components(self, admin, products, components):
        created = 0
        skipped = 0
        for link in PRODUCT_COMPONENT_LINKS:
            prod_idx, comp_idx, ref_des, qty, loc_desc, board, notes = link
            product = products[prod_idx]
            component = components[comp_idx]

            # Check for existing link (same product + component + designator)
            exists = ProductComponent.objects.filter(
                product=product,
                component=component,
                reference_designator=ref_des,
            ).exists()
            if exists:
                skipped += 1
                continue

            ProductComponent.objects.create(
                product=product,
                component=component,
                reference_designator=ref_des,
                quantity=qty,
                location_description=loc_desc,
                board_name=board,
                notes=notes,
                submission_level="basic",
                is_verified=True,
                verified_by=admin,
                created_by=admin,
            )
            created += 1

        self.stdout.write(
            f"Product-Components: {created} created, {skipped} already existed."
        )

    def _update_counts(self, products, components):
        for p in products:
            p.component_count = p.product_components.count()
            p.save(update_fields=["component_count"])
        for c in components:
            c.usage_count = c.product_components.count()
            c.save(update_fields=["usage_count"])
        self.stdout.write("Denormalized counts updated.")
