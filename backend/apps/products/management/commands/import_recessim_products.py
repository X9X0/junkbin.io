"""
Management command to import curated product teardown documentation from the
RECESSIM reverse-engineering wiki (https://wiki.recessim.com), licensed CC BY-SA 4.0.

Content (descriptions, component identifications, image selections) was
curated by reading each source wiki page; this command only handles the
mechanical work of fetching image bytes from the wiki and writing DB rows.

Usage:
    python manage.py import_recessim_products
    python manage.py import_recessim_products --flush  # delete existing and re-import
"""
import json
import urllib.parse
import urllib.request

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.components.models import Component, ProductComponent
from apps.products.models import Product, ProductImage

User = get_user_model()

WIKI_API = "https://wiki.recessim.com/w/api.php"
USER_AGENT = "junkbinio-import/1.0 (+https://junkbin.io)"


def fetch_wiki_file_bytes(filename):
    """Resolve a wiki File: page to its direct image URL and download it."""
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
    })
    req = urllib.request.Request(f"{WIKI_API}?{params}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    for page in data.get("query", {}).get("pages", {}).values():
        infos = page.get("imageinfo")
        if infos:
            img_req = urllib.request.Request(infos[0]["url"], headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(img_req, timeout=30) as r2:
                return r2.read()
    raise ValueError(f"no imageinfo for File:{filename}")


# Each dict: manufacturer/model_number/category/description/teardown_notes/
# source_url, plus curated `images` and `components` sub-lists. Attribution
# is appended to teardown_notes automatically in handle().
PRODUCTS = [
    {
        "manufacturer": "APC", "model_number": "Back-UPS ES 600", "category": "ups",
        "description": "The APC Back-UPS ES 600 is a 600VA consumer uninterruptible power supply (UPS) providing battery backup and surge protection for small electronics.",
        "teardown_notes": "Board model 640-1134-Z REV04, built around a Microchip PIC18F45J50 8-bit microcontroller. Community documentation covers the ICSP programming pinout and the RJ50 telecom/network surge-protection port pinout.",
        "source_url": "https://wiki.recessim.com/view/APC_Back_UPS_ES_600",
        "images": [
            {"filename": "APC Back UPS ES 600 PNG.png", "caption": "APC Back-UPS ES 600 overview", "type": "overview"},
            {"filename": "APC Back UPS ES 600 ICSP pinout.png", "caption": "ICSP programming header pinout", "type": "schematic"},
            {"filename": "APC Back UPS ES 600 RJ50 Pinout.png", "caption": "RJ50 telecom surge-protection port pinout", "type": "schematic"},
        ],
        "components": [
            {"part_number": "PIC18F45J50", "manufacturer": "Microchip Technology", "component_type": "mcu",
             "description": "8-bit PIC18 microcontroller, main system controller", "notes": "Identified as the UPS's main controller."},
        ],
    },
    {
        "manufacturer": "Apollo", "model_number": "AL-A26 Pager", "category": "pager",
        "description": "The Apollo Pilot AL-A26 is an alphanumeric POCSAG paging receiver that can be hand-programmed or reprogrammed for use on amateur radio frequencies.",
        "teardown_notes": "Documents full disassembly, the hand-programming menu system (frequency, RIC/CAPCODE, baud, contrast), and a reverse-engineering effort to dump the configuration EEPROM via exposed gold pads on the RF receiver PCB, using tools like a Bus Pirate or CH341A programmer.",
        "source_url": "https://wiki.recessim.com/view/Apollo_AL-A26_(Pager)",
        "images": [
            {"filename": "Front pager.jpg", "caption": "Front of the AL-A26", "type": "overview"},
            {"filename": "Back pager.jpg", "caption": "Back of the AL-A26", "type": "overview"},
            {"filename": "Mainboard front pager.jpg", "caption": "Main board from the front", "type": "pcb_top"},
            {"filename": "Mainboard back pager.jpg", "caption": "Main board from the back", "type": "pcb_bottom"},
        ],
        "components": [
            {"part_number": "CAT24WC16", "manufacturer": "Catalyst Semiconductor", "component_type": "eeprom",
             "description": "16-kbit I2C EEPROM storing pager configuration and passcode", "notes": "Main EEPROM located top-right of the board; target of the EEPROM-dumping reverse-engineering effort."},
            {"part_number": "SM8212B", "manufacturer": "NPC (Nippon Precision Circuits)", "component_type": "ic",
             "description": "FSK/POCSAG decoder IC for multiframe pagers", "notes": "Identified as the pager's POCSAG decoder chip."},
        ],
    },
    {
        "manufacturer": "B&G International (Nisene Technology Group)", "model_number": "Decapsulator Model 250", "category": "test_equipment",
        "description": "A programmable, temperature-controlled acid-etching IC decapsulator from the mid-1990s, used to remove epoxy packaging from ICs for failure analysis or reverse engineering via dual (nitric and sulphuric) acid etching.",
        "teardown_notes": "Documents both the acid-etching chamber unit and its separate controller unit. The controller's processor board runs a Motorola MC6803 8-bit microcontroller at 4.9152 MHz with external 8k RAM, 64k EEPROM, and a 256k EPROM; a separate I/O board drives the acid valves and lifting cylinder.",
        "source_url": "https://wiki.recessim.com/view/B&G_International_Decapsulator_Model_250",
        "images": [
            {"filename": "BG International Decapsulator Model 250.png", "caption": "B&G International Decapsulator Model 250", "type": "overview"},
            {"filename": "BG Model 250 Front.JPG", "caption": "Decapsulator with top and side covers removed", "type": "internal"},
            {"filename": "BG Model 250 Controller Processor Board.jpeg", "caption": "Processor board (Motorola MC6803 8-bit MCU)", "type": "pcb_top"},
            {"filename": "BG Model 250 Controller IO Board Front.jpeg", "caption": "IO Board used to drive valves in the acid-etching unit", "type": "pcb_top"},
        ],
        "components": [
            {"part_number": "MC6803", "manufacturer": "Motorola", "component_type": "mcu",
             "description": "8-bit microcontroller, controller board's main processor", "notes": "Runs at 4.9152 MHz on the controller's processor board."},
        ],
    },
    {
        "manufacturer": "Bio-Rad Laboratories", "model_number": "3000Xi", "category": "test_equipment",
        "description": "A microprocessor-controlled, high-voltage power supply (late 1980s-1990s) for laboratory electrophoresis techniques (SDS-PAGE, 2-D electrophoresis, blotting, isoelectric focusing), delivering a regulated DC output up to 3,000V/300mA/400W in constant-voltage, constant-current, or constant-power modes.",
        "teardown_notes": "In-depth reverse-engineering of the CPU Control Board (OEM No. 125B) and HV Controller Board (OEM No. 127 A/B), including full schematics, connector pinouts, and active-component identification for both boards.",
        "source_url": "https://wiki.recessim.com/view/BIO-RAD_3000Xi",
        "images": [
            {"filename": "BIO-RAD 3000Xi Overview Photo.jpg", "caption": "Bio-Rad 3000Xi overview", "type": "overview"},
            {"filename": "BIO-RAD_OEM_NO_125B_Top.jpg", "caption": "CPU Control Board (OEM No. 125B)", "type": "pcb_top"},
            {"filename": "BIO-RAD OEM NO 127A Top.jpg", "caption": "HV Controller Board 127A, top", "type": "pcb_top"},
            {"filename": "BIO-RAD OEM NO 127B Bottom.jpg", "caption": "HV Controller Board 127B, bottom", "type": "pcb_bottom"},
        ],
        "components": [
            {"part_number": "MC6809P", "manufacturer": "Motorola", "component_type": "mcu", "reference_designator": "M1",
             "description": "8-bit microprocessor, main CPU of the CPU Control Board", "notes": "Main CPU on OEM No. 125B."},
            {"part_number": "MC6821P", "manufacturer": "Motorola", "component_type": "ic", "reference_designator": "M?",
             "description": "Peripheral Interface Adapter (PIA)", "notes": "CPU Control Board peripheral I/O."},
            {"part_number": "MC6840P", "manufacturer": "Motorola", "component_type": "ic",
             "description": "Programmable timer (dual instance on CPU board)", "notes": "Timing generation on the CPU Control Board."},
            {"part_number": "CK2605", "manufacturer": "Signetics", "component_type": "ic", "reference_designator": "M7",
             "description": "FPGA used for glue logic and address decoding", "notes": "Handles address decode/control sequencing on the CPU Control Board."},
            {"part_number": "AD7543JN", "manufacturer": "Analog Devices", "component_type": "ic",
             "description": "12-bit DAC", "notes": "HV setpoint control DAC on the HV Controller Board."},
            {"part_number": "IR3M02", "manufacturer": "Sharp", "component_type": "regulator", "quantity": 2,
             "description": "PWM switching-regulator control IC (upgraded IR9494 with UVLO)", "notes": "Two devices, likely implementing independent constant-voltage/constant-current control loops."},
            {"part_number": "ICL7660CPA", "manufacturer": "Intersil", "component_type": "ic",
             "description": "Charge-pump voltage converter", "notes": "HV Controller Board support IC."},
        ],
    },
    {
        "manufacturer": "Amazon (Blink)", "model_number": "Sync Module 2", "category": "smart_home",
        "description": "The Blink Sync Module 2 is the hub appliance for Amazon Blink wireless home-security cameras, bridging up to ten local Blink cameras to Wi-Fi/cloud and providing local video storage via a USB flash drive.",
        "teardown_notes": "Two documented board revisions exist (distinguished by MCU placement): an 'Amazon Board' built around an NXP i.MX6 ULZ applications processor, and a 'Rev A0 Blink Board' built around a Qualcomm Atheros AR9331. Both revisions share the same Silicon Labs Si4455 sub-GHz transceiver for the camera-to-hub radio link.",
        "source_url": "https://wiki.recessim.com/view/Blink_SyncModule_2",
        "images": [
            {"filename": "Blink syncmodule2 photo1.jpg", "caption": "Front face of the BSM2", "type": "overview"},
            {"filename": "Photo2.jpg", "caption": "Back face of the BSM2", "type": "overview"},
            {"filename": "Photo5.jpg", "caption": "PCB view (top)", "type": "pcb_top"},
            {"filename": "Photo8.jpg", "caption": "PCB view (bottom)", "type": "pcb_bottom"},
        ],
        "components": [
            {"part_number": "MCIMX6Z0DVM09AB", "manufacturer": "NXP", "component_type": "mcu",
             "description": "ARM Cortex-A7 applications processor running Linux at 900MHz", "notes": "Amazon Board microcontroller."},
            {"part_number": "88W8987-NYE2", "manufacturer": "NXP", "component_type": "rf_module",
             "description": "2.4/5GHz Wi-Fi 5 + Bluetooth 5.2 combo module", "notes": "Amazon Board Wi-Fi/Bluetooth module."},
            {"part_number": "W25Q256JV", "manufacturer": "Winbond", "component_type": "eeprom",
             "description": "256Mbit dual/quad SPI NOR flash", "notes": "Amazon Board serial flash."},
            {"part_number": "IS43TR16640BL", "manufacturer": "ISSI", "component_type": "eeprom",
             "description": "1GB 16-bit DDR3 SDRAM", "notes": "Shared RAM part on both the Amazon Board and Rev A0 Blink Board."},
            {"part_number": "Si4455", "manufacturer": "Silicon Labs", "component_type": "rf_module",
             "description": "Sub-GHz 'EZRadio' FSK/OOK transceiver, 283-960MHz", "notes": "Camera-to-hub sub-GHz radio, shared across both board revisions (identified by markings 455A CQRX 220)."},
            {"part_number": "AR9331", "manufacturer": "Qualcomm Atheros", "component_type": "mcu",
             "description": "MIPS 24Kc @ 400MHz Wi-Fi SoC, used as both MCU and Wi-Fi module", "notes": "Rev A0 Blink Board variant."},
        ],
    },
    {
        "manufacturer": "Canon", "model_number": "PowerShot A3100 IS", "category": "camera",
        "description": "A 12.1MP point-and-shoot digital camera with a 1/2.3\" CCD sensor and optical image stabilization, released January 2010.",
        "teardown_notes": "Teardown of a dead unit (no power at battery terminals) covering CPU/DSP, CCD driver, audio/video, lens/IS, power, and flash sections. No official service manual was found; technical background sourced from the CHDK wiki firmware project.",
        "source_url": "https://wiki.recessim.com/view/Canon_PowerShot_A3100_IS",
        "images": [
            {"filename": "Canon PowerShot A3100 IS.jpg", "caption": "Canon PowerShot A3100 IS overview", "type": "overview"},
            {"filename": "Canon PowerShot A3100 IS Main Front.jpg", "caption": "Main PCB, front", "type": "pcb_top"},
            {"filename": "Canon PowerShot A3100 IS Main Back.jpg", "caption": "Main PCB, back", "type": "pcb_bottom"},
            {"filename": "Canon PowerShot A3100 IS ccd front.jpg", "caption": "CCD image sensor", "type": "closeup"},
        ],
        "components": [
            {"part_number": "K8P6415UQB", "manufacturer": "Samsung", "component_type": "eeprom",
             "description": "4Mx16 NOR flash memory, 16MB", "notes": "Main firmware/storage flash."},
            {"part_number": "MAX8680CE", "manufacturer": "Maxim Integrated", "component_type": "regulator",
             "description": "7-channel DC-DC power management IC", "notes": "Marked TL005; identified via power section teardown."},
        ],
    },
    {
        "manufacturer": "Canon", "model_number": "PowerShot G9", "category": "camera",
        "description": "A 12.1MP point-and-shoot digital camera with a 1/1.7\" CCD sensor and 6x optical image-stabilized zoom, released October 2007.",
        "teardown_notes": "Parts identification across the main PCB (CPU/DSP, CCD interface, lens motor driver, image stabilization, LCD driver, audio/video) and a separate power PCB. A service manual with an assembly diagram (but no schematic) exists online; firmware background sourced from the CHDK wiki project.",
        "source_url": "https://wiki.recessim.com/view/Canon_PowerShot_G9",
        "images": [
            {"filename": "Canon-powershot-g9.jpg", "caption": "Canon PowerShot G9 overview", "type": "overview"},
            {"filename": "Canon PowerShot G9 Main PCB Top.jpg", "caption": "Main PCB, top", "type": "pcb_top"},
            {"filename": "Canon PowerShot G9 Main PCB Back.jpg", "caption": "Main PCB, back", "type": "pcb_bottom"},
            {"filename": "Canon PowerShot G9 image sensor.jpg", "caption": "CCD image sensor", "type": "closeup"},
        ],
        "components": [
            {"part_number": "DIGIC III", "manufacturer": "Canon", "component_type": "ic", "reference_designator": "IC1001",
             "description": "Canon DIGIC III digital camera image processor SoC", "notes": "Main CPU/DSP, package-on-package with RAM/flash."},
            {"part_number": "HB0010A17E-E", "manufacturer": "Elpida Memory", "component_type": "eeprom", "reference_designator": "IC1001",
             "description": "DDR mobile RAM + NOR flash memory, package-on-package", "notes": "Stacked with the DIGIC III processor."},
            {"part_number": "WM1400G", "manufacturer": "Wolfson Microelectronics", "component_type": "ic", "reference_designator": "IC4501",
             "description": "Audio driver/codec", "notes": "Audio/video section."},
            {"part_number": "NJM2571", "manufacturer": "New Japan Radio (NJRC)", "component_type": "ic", "reference_designator": "IC4502",
             "description": "Low-voltage video amplifier with LPF", "notes": "Audio/video section."},
        ],
    },
    {
        "manufacturer": "Catalia Health", "model_number": "Mabu 2AK8Y-M0208", "category": "medical",
        "description": "Mabu is a tablet-form-factor personal healthcare companion robot from Catalia Health, used for patient engagement and health coaching.",
        "teardown_notes": "Documentation compiled from FCC ID filing photos and public teardown notes rather than a hands-on physical teardown; no photos are yet hosted on this wiki page. Identified subsystems include a RockChip RK3228 application SoC, 2.4GHz Wi-Fi/Bluetooth and LTE antennas, and a camera/light sensor.",
        "source_url": "https://wiki.recessim.com/view/Catalia_Health_Mabu_2AK8Y-M0208",
        "images": [],
        "components": [
            {"part_number": "RK3228", "manufacturer": "Rockchip", "component_type": "ic",
             "description": "ARM SoC application processor", "notes": "Identified from the FCC internal photos as the device's main SoC."},
        ],
    },
    {
        "manufacturer": "PerSeptive Biosystems", "model_number": "CytoFluor 4000", "category": "test_equipment",
        "description": "A fluorescence multi-well plate reader used in laboratory bioassay work. Manufacturer attribution to PerSeptive Biosystems is inferred from the associated user-manual PDF and era of the device; later generations of this product line passed through Applied Biosystems/Thermo Fisher.",
        "teardown_notes": "Documents the serial command protocol (plate load/eject, filter positioning, lamp control, shake, well read) and a partial list of major ICs identified on the control board, sourced from the official user manual rather than a full physical teardown.",
        "source_url": "https://wiki.recessim.com/view/Cytofluor_4000",
        "images": [],
        "components": [
            {"part_number": "24LC01B", "manufacturer": "Catalyst Semiconductor", "component_type": "eeprom",
             "description": "1-kbit I2C EEPROM", "notes": "Listed as one of the major ICs in the control system."},
            {"part_number": "CY545", "manufacturer": "Cypress Semiconductor", "component_type": "ic",
             "description": "Stepper motor system controller", "notes": "Drives the plate-loading stepper motor system."},
        ],
    },
    {
        "manufacturer": "GRAW Radiosondes GmbH & Co. KG", "model_number": "DFM-17 Radiosonde", "category": "other",
        "description": "The DFM-17 is a balloon-launched radiosonde used for meteorological (weather balloon) sounding, transmitting sensor telemetry over radio to ground stations.",
        "teardown_notes": "Extensive reverse-engineering of the PCB's IC attachment points: an STM32F100R8T6B ARM MCU, a u-blox M8 GNSS module, a Silicon Labs Si4063 sub-GHz transmitter, several analog switch/mux ICs, and an NFC/RFID EEPROM tag. Covers SWD programming via an ST-Link, using the same VTRef/GND/SWDIO/SWDCLK/RST connections as the Vaisala RS41.",
        "source_url": "https://wiki.recessim.com/view/DFM-17_Radiosonde",
        "images": [
            {"filename": "DFM-17 Radiosonde in hand.jpg", "caption": "DFM-17 Radiosonde", "type": "overview"},
            {"filename": "DFM-17 Uref overlay.jpg", "caption": "Top view of PCB with reference designators overlaid", "type": "pcb_top"},
            {"filename": "DFM-17 Internal.jpg", "caption": "Internal view of the DFM-17", "type": "internal"},
            {"filename": "DFM-17 Battery Holder.jpg", "caption": "Bottom side of the PCB", "type": "pcb_bottom"},
        ],
        "components": [
            {"part_number": "STM32F100R8T6B", "manufacturer": "STMicroelectronics", "component_type": "mcu",
             "description": "ARM Cortex-M3 MCU, 24MHz, 8KB RAM, 64KB Flash", "notes": "Main SoC. Some recent production batches reportedly use knockoff/counterfeit STM32 parts."},
            {"part_number": "Si4063", "manufacturer": "Silicon Labs", "component_type": "rf_module", "reference_designator": "U10",
             "description": "Sub-GHz FSK transmitter", "notes": "Main radio transmitter, on SPI_1."},
            {"part_number": "u-blox M8", "manufacturer": "u-blox", "component_type": "rf_module", "reference_designator": "U11",
             "description": "GNSS positioning module", "notes": "On USART_2."},
            {"part_number": "STG719", "manufacturer": "STMicroelectronics", "component_type": "switch", "reference_designator": "U2, U3, U4, U5, U7", "quantity": 5,
             "description": "SOT-23-6 DPST analog switch", "notes": "Multiple instances used for signal routing."},
            {"part_number": "SN74LV4053", "manufacturer": "Texas Instruments", "component_type": "ic", "reference_designator": "U8",
             "description": "Triple 2-channel analog mux/demux", "notes": "Analog input routing to the STM32's ADC."},
            {"part_number": "LMV761", "manufacturer": "Texas Instruments", "component_type": "opamp", "reference_designator": "U9",
             "description": "Low-voltage precision comparator", "notes": "Part of the analog front-end."},
        ],
    },
    {
        "manufacturer": "Dali", "model_number": "D8X3N Thermal Camera", "category": "security_cam",
        "description": "The Dali D8X3N is a network thermal-imaging camera module providing ONVIF/RTSP streaming, built around a HiSilicon SoC running embedded Linux.",
        "teardown_notes": "Multi-board stack: network/GPIO board, SoC board, FPGA board (with PMIC, video DAC, and SPI flash), and sensor control/ADC board. Documents patching the device firmware for root/telnet access, raw thermal data extraction over the web API, and SPI-flash-based bad-pixel/flatfield calibration map recovery. The onboard flash was identified as a Winbond 25Q128JV SPI flash holding the FPGA bitstream, calibration maps, and settings.",
        "source_url": "https://wiki.recessim.com/view/Dali_D8X3N_Thermal_Camera",
        "images": [
            {"filename": "Dali D8X3N Module.jpg", "caption": "Dali D8X3N thermal camera module", "type": "overview"},
            {"filename": "Dali D8X3N SoC Board front.jpeg", "caption": "SoC board, front", "type": "pcb_top"},
            {"filename": "Dali D8X3N FPGA Board Front.jpeg", "caption": "FPGA board (with PMIC), front", "type": "pcb_top"},
            {"filename": "Dali D8X3N SoC Board Back.jpeg", "caption": "SoC board, back", "type": "pcb_bottom"},
        ],
        "components": [
            {"part_number": "W25Q128JV", "manufacturer": "Winbond", "component_type": "eeprom",
             "description": "128Mbit SPI NOR flash", "notes": "Holds the FPGA bitstream, dead-pixel/flatfield maps, and device settings."},
        ],
    },
    {
        "manufacturer": "Digitech", "model_number": "XC0324", "category": "iot",
        "description": "A small wireless remote thermometer sensor sold under the Digitech brand, transmitting on 433.92MHz (readable with RTL_433) and sharing its board design with the related XC0321/XC0322 models.",
        "teardown_notes": "Brief teardown noting a ~32kHz crystal reference and an unpopulated second LED footprint (LED2) on the PCB. Device weighs 27g without batteries.",
        "source_url": "https://wiki.recessim.com/view/Digitech-XC0324",
        "images": [
            {"filename": "XC0234 Front.jpg", "caption": "Digitech XC0324 sensor, exterior", "type": "overview"},
            {"filename": "20210917 105103.jpg", "caption": "Front and back of the PCB", "type": "pcb_top"},
            {"filename": "20210917 093752.jpg", "caption": "PCB detail", "type": "pcb_bottom"},
        ],
        "components": [],
    },
    {
        "manufacturer": "Disney", "model_number": "Flix Camcorder", "category": "camcorder",
        "description": "A toy camcorder for children, built around a Zoran Coach camera SoC — the dominant point-and-shoot camera processor family of the late 2000s/early 2010s (Zoran's camera IP was later sold to Qualcomm via CSR).",
        "teardown_notes": "Notably simple construction using right-angle pin headers rather than flex cables between boards (except the display), making it an easy target for signal tapping. Has a working serial debug port; documents boot logs, power-down behavior, and image capture/settings-mode navigation over serial.",
        "source_url": "https://wiki.recessim.com/view/Disney_Flix_Camcorder",
        "images": [
            {"filename": "Disney Flix Camcorder.jpg", "caption": "Disney Flix Camcorder overview", "type": "overview"},
            {"filename": "Disney Flix Camcorder Main PCB Front.jpg", "caption": "Main PCB, front", "type": "pcb_top"},
            {"filename": "Disney Flix Camcorder Main PCB back.jpg", "caption": "Main PCB, back", "type": "pcb_bottom"},
            {"filename": "Disney Flix Sensor PCB back.jpg", "caption": "Sensor PCB, back", "type": "closeup"},
        ],
        "components": [
            {"part_number": "ZR36440BGCF", "manufacturer": "Zoran Corporation", "component_type": "ic", "reference_designator": "U1",
             "description": "'Coach 6e' digital camera processor SoC", "notes": "Main image/video processing SoC."},
        ],
    },
    {
        "manufacturer": "GE Healthcare", "model_number": "FlashPad Digital X-ray Detector", "category": "medical",
        "description": "A wireless digital flat-panel X-ray detector used in medical radiography, supporting Ethernet and wireless connectivity, onboard shock/drop event logging, and script-driven acquisition sequences.",
        "teardown_notes": "In-depth protocol reverse-engineering covering the network setup handshake, script-based acquisition sequencing (dark/offset and standard acquisitions), host registration/pairing, drop-and-shock event log readout, and a full internal flash dump with layout analysis. Board built around an Altera Cyclone III FPGA and an Altera EPM570 CPLD.",
        "source_url": "https://wiki.recessim.com/view/GE_Medical_Flashpad_Digital_Xray_Detector",
        "images": [
            {"filename": "GE Flashpad.jpg", "caption": "GE FlashPad detector overview", "type": "overview"},
            {"filename": "Ge flashpad main pcb closeup1.jpg", "caption": "Main PCB area with Altera Cyclone III FPGA", "type": "pcb_top"},
            {"filename": "Ge flashpad main pcb closeup 7.jpg", "caption": "Spansion GL512P10FF1R1 512Mbit NOR flash", "type": "closeup"},
            {"filename": "Ge flashpad powersupply pcb in handle.jpg", "caption": "Power supply PCB", "type": "internal"},
        ],
        "components": [
            {"part_number": "EPM570F100C5N", "manufacturer": "Altera", "component_type": "ic",
             "description": "CPLD", "notes": "Identified on the main PCB."},
            {"part_number": "AD7892", "manufacturer": "Analog Devices", "component_type": "ic",
             "description": "600ksps 12-bit ADC", "notes": "Main PCB analog front-end."},
            {"part_number": "SN74LVC8T245", "manufacturer": "Texas Instruments", "component_type": "ic",
             "description": "8-bit bus transceiver", "notes": "Main PCB data bus buffering."},
            {"part_number": "AD9764AR", "manufacturer": "Analog Devices", "component_type": "ic",
             "description": "14-bit, 125MSPS DAC", "notes": "Main PCB analog output."},
            {"part_number": "DS1682", "manufacturer": "Maxim Integrated", "component_type": "ic",
             "description": "Integrated elapsed-time recorder", "notes": "Used for shock/drop event timestamping."},
            {"part_number": "GL512P10FF1R1", "manufacturer": "Spansion", "component_type": "eeprom",
             "description": "512Mbit (64MB) parallel NOR flash", "notes": "Holds firmware, FPGA configuration, and recovered data files; target of the internal flash dump."},
            {"part_number": "24LC256", "manufacturer": "Microchip Technology", "component_type": "eeprom",
             "description": "32K x8 I2C EEPROM", "notes": "Stores accelerometer/shock-log events, mirroring the flash-based log."},
        ],
    },
    {
        "manufacturer": "Hamamatsu", "model_number": "C9321SK CMOS X-ray Sensor", "category": "medical",
        "description": "The C9321SK-05 is a megapixel (1056x1056, 50-micron pixel pitch) CMOS flat-panel X-ray image sensor using a gadox scintillator on a fiber-optic plate, offering up to 27fps real-time imaging with 2x2 binning and a 6-million-Roentgen guaranteed lifetime at 150kVp.",
        "teardown_notes": "Exterior and internal teardown photos of the sensor and its control board (marked XM06D).",
        "source_url": "https://wiki.recessim.com/view/Hamamatsu_C9321SK_CMOS_X-ray_Sensor",
        "images": [
            {"filename": "Hamamatsu C9321SK 6812207 Overview Picture.jpg", "caption": "Hamamatsu C9321SK overview", "type": "overview"},
            {"filename": "Hamamatsu C9321SK 6812207 XM06D-ControlBoard Top.jpg", "caption": "Control board (XM06D), top", "type": "pcb_top"},
            {"filename": "Hamamatsu C9321SK 6812207 XM06D-ControlBoard Bottom.jpg", "caption": "Control board (XM06D), bottom", "type": "pcb_bottom"},
            {"filename": "Hamamatsu C9321SK 6812207 XM06D-Sensor Top.jpg", "caption": "Sensor board (XM06D), top", "type": "closeup"},
        ],
        "components": [],
    },
    {
        "manufacturer": "Hughes", "model_number": "HNS 9101 BGAN Satellite Modem", "category": "modem",
        "description": "A Broadband Global Area Network (BGAN) satellite terminal, providing UMTS-compatible broadband connectivity over Inmarsat's L-Band satellite network (RX 1525.0-1559.0MHz, TX 1626.5-1660.5MHz), standardized under ETSI GMR-1.",
        "teardown_notes": "Research effort aimed at accessing debugging modes to decode Inmarsat BGAN control channels, motivated by parallel work in the Osmocom GMR project on the related GMR-1-based Thuraya/RBGAN network.",
        "source_url": "https://wiki.recessim.com/view/Hughes_HNS_9101_Inmarsat_Regional_BGAN_Satellite_Modem",
        "images": [],
        "components": [],
    },
    {
        "manufacturer": "Instant Brands", "model_number": "Omni Pro 18 Toaster Oven and Air Fryer", "category": "kitchen",
        "description": "A combination toaster oven and air fryer from Instant Brands' Omni Pro line.",
        "teardown_notes": "Recovered as e-waste with a partially failed display and touch controls. The display/button panel communicates with the main power/relay board over a slow (~600-1250bps) serial link; reverse-engineering of this protocol has reproduced basic beeps and status LEDs using an ESP32-S3 running MicroPython, based on oscilloscope and logic-analyzer captures. The relay board's 16-channel constant-current LED driver was identified as a Macroblock MBI5124.",
        "source_url": "https://wiki.recessim.com/view/Instant_Omni_Pro_18_Toaster_Oven_and_Air_Fryer",
        "images": [
            {"filename": "Instant Omni Pro Front Exterior Light On 400 F 10 Minute Start Cancel.jpg", "caption": "Instant Omni Pro 18, front panel lit", "type": "overview"},
        ],
        "components": [
            {"part_number": "MBI5124", "manufacturer": "Macroblock", "component_type": "ic",
             "description": "16-channel constant-current LED driver IC", "notes": "On the relay/display board."},
        ],
    },
    {
        "manufacturer": "Grand Idea Studio", "model_number": "JTAGulator", "category": "test_equipment",
        "description": "An open-source tool designed by Joe Grand to help locate On-Chip Debugging (OCD) interfaces — JTAG ports and UARTs — on embedded devices.",
        "teardown_notes": "Documents a JTAG-discovery failure investigated against a Kenwood TH-D74 radio: oscilloscope probing found the TRST line was pulled low via a 2.2k resistor per the target chip's datasheet, and the JTAGulator could not drive it high enough to be recognized. Adding a 1k pull-up resistor to the TRST line resolved the issue.",
        "source_url": "https://wiki.recessim.com/view/JTAGulator",
        "images": [
            {"filename": "JTAGulator and Kenwood TH-D74.jpg", "caption": "JTAGulator connected to a Kenwood TH-D74 during a JTAG-discovery session", "type": "overview"},
            {"filename": "1 TRST no pullup.jpg", "caption": "Oscilloscope capture: TRST line without pull-up, driven too low", "type": "closeup"},
            {"filename": "3 TRST pullup.jpg", "caption": "Oscilloscope capture: TRST line with an added 1k pull-up, now within spec", "type": "closeup"},
            {"filename": "5 TRST Overview.jpg", "caption": "Test setup with the added pull-up resistor", "type": "internal"},
        ],
        "components": [],
    },
    {
        "manufacturer": "Kenwood", "model_number": "TH-D74A", "category": "radio",
        "description": "A tri-band handheld amateur radio transceiver with built-in APRS/GPS, D-STAR digital voice, and Bluetooth.",
        "teardown_notes": "Full teardown video and photo set covering the processor board, transceiver board, FM radio module, and mechanical assembly. Reverse-engineering efforts aimed at obtaining firmware include JTAG boot-mode pin identification (via the OMAP-L138 applications processor) and a proposed hardware attack of desoldering the flash chip for direct reads.",
        "source_url": "https://wiki.recessim.com/view/Kenwood_TH-D74A",
        "images": [
            {"filename": "TH-D74A.jpg", "caption": "Kenwood TH-D74A, fully assembled", "type": "overview"},
            {"filename": "TH-D74A Processor board Top.jpg", "caption": "Processor board, top", "type": "pcb_top"},
            {"filename": "TH-D74A Transceiver board top.jpg", "caption": "Transceiver board, top", "type": "pcb_top"},
            {"filename": "TH-D74A Processor board bottom.jpg", "caption": "Processor board, bottom", "type": "pcb_bottom"},
        ],
        "components": [
            {"part_number": "OMAP-L138", "manufacturer": "Texas Instruments", "component_type": "mcu", "reference_designator": "IC-702",
             "description": "Applications processor", "notes": "Main processor; boot-mode pin (Boot[]) test points identified for JTAG/reverse-engineering purposes."},
            {"part_number": "WM8940", "manufacturer": "Wolfson Microelectronics", "component_type": "ic", "reference_designator": "IC-707",
             "description": "Audio codec (same family as the confirmed marking, exact part not a precise match)", "notes": "Datasheet identification not exact — same product family as the marked part."},
            {"part_number": "LM8325-1", "manufacturer": "Texas Instruments", "component_type": "ic", "reference_designator": "IC-730",
             "description": "Keyscan/IO-expander", "notes": "Front-panel key scanning."},
        ],
    },
    {
        "manufacturer": "Kobalt", "model_number": "KRC 40-06", "category": "charger",
        "description": "A battery charger for Kobalt (Lowe's) 40V cordless outdoor power tools such as string trimmers and leaf blowers.",
        "teardown_notes": "Repair log for a unit damaged by a nearby lightning strike. Circuit topology: 120VAC input through fuse, common-mode choke, and full-wave bridge rectifier to 172VDC, feeding a Power Integrations TOP386EG flyback switcher; secondary-side output is rectified through an MBR2560CT Schottky diode, with an LTV-817B optocoupler providing primary-side feedback. Board is conformal-coated.",
        "source_url": "https://wiki.recessim.com/view/Kobalt_KRC_40-06",
        "images": [],
        "components": [
            {"part_number": "TOP386EG", "manufacturer": "Power Integrations", "component_type": "regulator",
             "description": "Off-line flyback switcher IC", "notes": "Primary-side switching converter driving the charger's transformer."},
            {"part_number": "MBR2560CT", "manufacturer": "ON Semiconductor", "component_type": "diode",
             "description": "Schottky rectifier", "notes": "Secondary-side output rectification."},
            {"part_number": "LTV-817B", "manufacturer": "Lite-On", "component_type": "ic",
             "description": "Optocoupler", "notes": "Provides isolated feedback to the TOP386EG switcher."},
        ],
    },
    {
        "manufacturer": "Lockheed Martin Sippican", "model_number": "LMS-6 Radiosonde", "category": "other",
        "description": "The LMS-6 is a balloon-launched radiosonde used for meteorological (weather balloon) sounding, transmitting sensor telemetry to ground stations.",
        "teardown_notes": "Extensive reverse-engineering effort covering the RF transmitter path (filter, matching network, broadband amplifier), a relative-humidity sensing circuit, original ST7 firmware analysis (GPIO/MCC/ADC/interrupt configuration disassembled in IDA Pro), and in-circuit ST7 programming details including a card-edge interface and eFuse behavior.",
        "source_url": "https://wiki.recessim.com/view/LMS-6_Radiosonde",
        "images": [
            {"filename": "LMS-6 Radiosonde.jpg", "caption": "LMS-6 Radiosonde", "type": "overview"},
            {"filename": "LMS6 bottom.jpg", "caption": "PCB, bottom", "type": "pcb_bottom"},
            {"filename": "20200926 203639.jpg", "caption": "PCB, top", "type": "pcb_top"},
            {"filename": "LMS6 TX Path Schematic.svg", "caption": "RF transmitter path schematic (reverse-engineered)", "type": "schematic"},
        ],
        "components": [
            {"part_number": "ST72F324J6T6B", "manufacturer": "STMicroelectronics", "component_type": "mcu",
             "description": "ST7-family 8-bit microcontroller", "notes": "Main microcontroller (marked 72F324J6T6)."},
            {"part_number": "CC1050", "manufacturer": "Texas Instruments (Chipcon)", "component_type": "rf_module",
             "description": "Sub-GHz FSK transceiver", "notes": "Main RF transmitter, referenced via its frequency-register calculator based on a 14.7456MHz crystal."},
            {"part_number": "CD4040BPW", "manufacturer": "Texas Instruments", "component_type": "ic", "reference_designator": "U13",
             "description": "12-stage ripple-carry binary counter/divider", "notes": "Identified via TI part-marking lookup (package marked CM040B)."},
            {"part_number": "LMV761MF", "manufacturer": "Texas Instruments", "component_type": "opamp", "reference_designator": "U16",
             "description": "Low-voltage precision comparator, SOT-23", "notes": "Identified via TI part-marking lookup (package marked C22A)."},
        ],
    },
    {
        "manufacturer": "Landis+Gyr", "model_number": "Integrated WanGate Radio (IWR)", "category": "industrial",
        "description": "A wide-area-network gateway radio used in Landis+Gyr AMI (advanced metering infrastructure) deployments to relay smart-meter data. Documents two hardware generations: the earlier Metricom Utilinet IWR Series II, and the newer, smaller Cellnet Technology Gridstream Series 4 (Cellnet was acquired into the Landis+Gyr product line).",
        "teardown_notes": "The Series II radio uses discrete components to build up its RF transmit/receive circuit and stores its code in an EEPROM with a jumper-selectable test mode; the newer Gridstream Series 4 radio is considerably smaller, uses a single integrated transceiver IC in place of the discrete RF circuit, and increases transmission power.",
        "source_url": "https://wiki.recessim.com/view/Landis+Gyr_Integrated_WanGate_Radio_(IWR)",
        "images": [
            {"filename": "Metricom Utilinet IWR Series II - Case External.jpg", "caption": "Metricom Utilinet IWR Series II", "type": "overview"},
            {"filename": "Metricom Utilinet IWR Series II - Processor Board.jpg", "caption": "Series II processor board: EEPROM for code storage, test-mode jumper", "type": "pcb_top"},
            {"filename": "LandisGyrWangateRadio1.JPG", "caption": "Cellnet Technology Gridstream Series 4", "type": "overview"},
            {"filename": "LandisGyrWangateRadio3.JPG", "caption": "Gridstream Series 4: smaller, single integrated transceiver IC", "type": "pcb_top"},
        ],
        "components": [],
    },
    {
        "manufacturer": "Landis+Gyr", "model_number": "SGP+M", "category": "industrial",
        "description": "SGP+M (Sistema de Gestão de Perdas e Medição — System for Management of Losses and Metering) is a Landis+Gyr smart-metering system deployed in Brazil, comprising Metering Modules, Secondary Concentrators, and Primary Concentrators that relay usage data via FHSS radio and GPRS.",
        "teardown_notes": "Documentation compiled from observation and public research rather than direct hardware access. The associated Smart Reading Terminal (TLI, Terminal de Leitura Inteligente) was accessible and was found to contain a Zilog Z8F0421 microcontroller, an RF receiver IC, and an LCD driver, with a factory-locked debug header.",
        "source_url": "https://wiki.recessim.com/view/Landis+Gyr_SGP+M",
        "images": [
            {"filename": "SGP+M Meter Module for Secondary Concentrator.png", "caption": "Metering Module for Secondary Concentrator", "type": "other"},
            {"filename": "SGP+M Secondary Concentrator.png", "caption": "Secondary Concentrator", "type": "other"},
            {"filename": "SGP+M Primary Concentrator.png", "caption": "Primary Concentrator", "type": "other"},
            {"filename": "L+G SGP+M TLI.jpg", "caption": "TLI Smart Reading Terminal", "type": "other"},
        ],
        "components": [
            {"part_number": "Z8F0421", "manufacturer": "Zilog", "component_type": "mcu",
             "description": "Z8 Encore microcontroller", "notes": "TLI Smart Reading Terminal's main MCU; debug header is factory-locked, requiring Z8 Encore bypass mode."},
            {"part_number": "ATA5744N", "manufacturer": "Atmel (Microchip Technology)", "component_type": "rf_module",
             "description": "RF receiver IC", "notes": "TLI Smart Reading Terminal's RF receive path."},
        ],
    },
    {
        "manufacturer": "Lantronix", "model_number": "MSS100", "category": "other",
        "description": "A serial-to-Ethernet device server produced by Lantronix, allowing legacy serial equipment to be bridged onto an Ethernet/IP network.",
        "teardown_notes": "Includes a documented component table cross-referencing part markings to manufacturers. Notable for being exposed to the public Internet in small numbers, alongside several hundred honeypots mimicking it. Built around a NetSilicon NET+ARM (ARM7TDMI) processor.",
        "source_url": "https://wiki.recessim.com/view/MSS100",
        "images": [
            {"filename": "Lantronix MSS100 external.jpg", "caption": "MSS100 case front, \"Retro Teal\" branding", "type": "overview"},
            {"filename": "Internal-casewide.jpg", "caption": "Wide angle photo of the circuit board, top", "type": "pcb_top"},
            {"filename": "Internal-bottomwide.jpg", "caption": "Wide angle photo of the circuit board, bottom", "type": "pcb_bottom"},
            {"filename": "Internal-headers1.jpg", "caption": "Internal headers close-up", "type": "closeup"},
        ],
        "components": [
            {"part_number": "LXT970AQC", "manufacturer": "Intel Corporation", "component_type": "ic",
             "description": "Dual-speed Ethernet transceiver", "notes": "From the documented component table."},
            {"part_number": "AM29LV800BT-120EC", "manufacturer": "Advanced Micro Devices", "component_type": "eeprom",
             "description": "CMOS boot flash", "notes": "From the documented component table."},
            {"part_number": "MT4LC1M16C3", "manufacturer": "Micron", "component_type": "eeprom", "quantity": 2,
             "description": "16Meg FPM DRAM", "notes": "Two instances, from the documented component table."},
            {"part_number": "MC33269", "manufacturer": "ON Semiconductor", "component_type": "regulator",
             "description": "Voltage regulator", "notes": "Marked 269-3 XAUY; from the documented component table."},
            {"part_number": "7705AC", "manufacturer": "Texas Instruments", "component_type": "ic",
             "description": "Supply voltage supervisor", "notes": "From the documented component table."},
            {"part_number": "HIN208ECA", "manufacturer": "Renesas", "component_type": "ic",
             "description": "RS-232 transmitter/receiver", "notes": "From the documented component table."},
            {"part_number": "NET+ARM", "manufacturer": "NetSilicon", "component_type": "mcu",
             "description": "32-bit ARM7TDMI RISC processor", "notes": "Main CPU, marked '55595B'; from the documented component table."},
        ],
    },
    {
        "manufacturer": "Masimo", "model_number": "Neo SpO2 Sensor (Single Patient Use)", "category": "medical",
        "description": "A single-use, disposable Masimo pulse-oximetry (SpO2) sensor designed for neonatal patients, worn on a finger via an elastic adhesive band and connected via an 18-inch cable to a 9-pin connector.",
        "teardown_notes": "Documented from the manufacturer's professional product listing; no photos or component-level teardown are yet hosted on this wiki page.",
        "source_url": "https://wiki.recessim.com/view/Masimo_Neo_SpO2_Sensor_Single_Patient_Use_Disposable",
        "images": [],
        "components": [],
    },
    {
        "manufacturer": "Master Meter", "model_number": "3G Mobile AMR", "category": "industrial",
        "description": "A DIALOG 3D-series endpoint containing an RF transceiver, used to relay water-consumption data in Automatic Meter Reading (AMR) systems (FCC ID: NTAXMETER21).",
        "teardown_notes": "PCB has an optical sensor to read the water meter dial position, an antenna-side reed switch (likely for magnetic-tampering detection), and two batteries soldered directly to the board.",
        "source_url": "https://wiki.recessim.com/view/Master_Meter_3G_Mobile_AMR",
        "images": [
            {"filename": "MasterMeter3G InstalledUnit.jpeg", "caption": "Installed unit", "type": "overview"},
            {"filename": "MasterMeter3G PCBTop-antenna.jpeg", "caption": "PCB top, with antenna", "type": "pcb_top"},
            {"filename": "MasterMeter3G PCBBottom.JPG", "caption": "PCB bottom, RF circuitry", "type": "pcb_bottom"},
            {"filename": "MasterMeter3G TLMW301 (CC1100).jpg", "caption": "TLMW301 IC, identified as a relabeled TI (Chipcon) CC1100", "type": "closeup"},
        ],
        "components": [
            {"part_number": "MSP430F2370", "manufacturer": "Texas Instruments", "component_type": "mcu",
             "description": "16-bit MSP430 microcontroller", "notes": "Unlabeled IC on the PCB top, identified by markings."},
            {"part_number": "CC1100", "manufacturer": "Texas Instruments (Chipcon)", "component_type": "rf_module",
             "description": "Sub-GHz RF transceiver", "notes": "Board's RF IC is marked TLMW301, identified as a relabeled TI CC1100 by its logo."},
        ],
    },
    {
        "manufacturer": "Miltel", "model_number": "SpeedRead STx", "category": "industrial",
        "description": "An external pulsed-reader (transmitter) used with wireless water-meter networks, separate from the meter itself, relaying pulse counts from up to four (or more) meter sensors to a repeater or concentrator.",
        "teardown_notes": "Contains a battery, a PCB with a firmware-read-protected PIC microcontroller, and an FM encoder. Each connected probe uses a reed switch pulsed by the meter's spinner; the microcontroller encodes each pulse as one of two PWM frequencies before FM transmission (one-way only).",
        "source_url": "https://wiki.recessim.com/view/Miltel_SpeedRead_STx",
        "images": [],
        "components": [],
    },
    {
        "manufacturer": "Motorola", "model_number": "Advisor Pager", "category": "pager",
        "description": "A pager from Motorola's Advisor line.",
        "teardown_notes": "Documents changing the pager's receive frequency via a custom-cut crystal: to achieve 439.9875MHz, a 3rd-overtone series-resonant crystal cut to 49.37634375MHz (UM-1 holder) was sourced from KRYSTALY (Hradec Kralove, Czech Republic).",
        "source_url": "https://wiki.recessim.com/view/Motorola_Advisor_(Pager)",
        "images": [],
        "components": [],
    },
    {
        "manufacturer": "Neato Robotics", "model_number": "XV-11", "category": "other",
        "description": "A robot vacuum notable for including a low-cost 360-degree LIDAR distance scanner, which can be used standalone in other robotics projects or interfaced within the XV-11 via the Robot Operating System (ROS).",
        "teardown_notes": "Extensive documentation covering ROS integration, LIDAR API commands and data formats across firmware versions, motor control commands, an open-source Linux bootloader with console access, and multiple PCB hardware revisions. Content migrated from the now-defunct xv11hacking.com community site.",
        "source_url": "https://wiki.recessim.com/view/Neato_XV-11",
        "images": [
            {"filename": "Neato XV-11.jpg", "caption": "Neato XV-11 overview", "type": "overview"},
            {"filename": "Neato XV-11 PCB Rev64 Top.jpg", "caption": "Main PCB Rev. 64, top", "type": "pcb_top"},
            {"filename": "Neato XV-11 PCB Rev64 Bottom.jpg", "caption": "Main PCB Rev. 64, bottom", "type": "pcb_bottom"},
            {"filename": "LIDAR mounted on PCB.jpg", "caption": "LIDAR scanner mounted on its interface PCB", "type": "closeup"},
        ],
        "components": [
            {"part_number": "AT91SAM9XE128", "manufacturer": "Atmel (Microchip Technology)", "component_type": "mcu",
             "description": "ARM9 SoC", "notes": "Main (robot-body) controller with external memory."},
            {"part_number": "LPC3131", "manufacturer": "NXP", "component_type": "mcu",
             "description": "ARM9 SoC used with Linux/u-boot", "notes": "Referenced in the recovered LinuxSrc/boot/arch/arm/cpu/lpc313 bootloader source path."},
        ],
    },
    {
        "manufacturer": "Panasonic", "model_number": "Toughpad FZ-G1 MK4", "category": "tablet",
        "description": "A portable, rugged industrial field tablet computer from Panasonic's Toughpad line, used across construction, defense, public safety, healthcare, and utility/telecom industries.",
        "teardown_notes": "Covers common failure points and repair notes for both the MK4 and MK5 revisions, including a TPS51367 buck converter failure mode that can kill the CPU or RAM, and documents the CPU, audio codec, and TPM changes made between the MK4 and MK5 revisions.",
        "source_url": "https://wiki.recessim.com/view/Panasonic_Toughpad_FZ-G1_MK4",
        "images": [
            {"filename": "Mb breakdown.jpg", "caption": "Mainboard breakdown (silkscreen: DHLB1030ZD/X1)", "type": "pcb_top"},
            {"filename": "Signature ALC256 MK4.jpg", "caption": "Shorted ALC256 audio codec on the FZ-G1 MK4", "type": "closeup"},
            {"filename": "ALC231 schematic.png", "caption": "ALC231 schematic (closest available match)", "type": "schematic"},
        ],
        "components": [
            {"part_number": "SR2F0", "manufacturer": "Intel", "component_type": "ic",
             "description": "Intel Core i5-6300U CPU (MK4 revision)", "notes": "Changed to SR340 (Core i5-7300U) in the MK5 revision."},
            {"part_number": "ALC256", "manufacturer": "Realtek", "component_type": "ic",
             "description": "Audio codec (MK4 revision)", "notes": "Common failure point (found shorted); changed to ALC295 in the MK5 revision."},
            {"part_number": "TPS51367", "manufacturer": "Texas Instruments", "component_type": "regulator",
             "description": "3V-22V, 12A synchronous buck converter", "notes": "Failure of this part can take out the CPU or RAM."},
        ],
    },
    {
        "manufacturer": "Sony", "model_number": "PlayStation 5", "category": "gaming",
        "description": "Sony's ninth-generation home video game console.",
        "teardown_notes": "Focused on hardware measurements, electrical characteristics, and repair diagnostics: cooling/thermal design (blower fan, liquid-metal TIM application and dust-accumulation susceptibility), power-rail voltage/resistance reference tables for the EDM-020 board revision, and named ICs found during a board-level repair of components knocked off an EDM-010 revision board.",
        "source_url": "https://wiki.recessim.com/view/PlayStation_5_(PS5)",
        "images": [
            {"filename": "PS5_PCB_EDM-020_Side_A.jpg", "caption": "EDM-020 board revision, side A", "type": "pcb_top"},
            {"filename": "PS5_PCB_EDM-020_Side_B.jpg", "caption": "EDM-020 board revision, side B", "type": "pcb_bottom"},
            {"filename": "EDM-020 AF01 Protection Switch.jpg", "caption": "AOZ1351DI-01 USB-PD/VBUS protection IC location", "type": "closeup"},
        ],
        "components": [
            {"part_number": "MN864739", "manufacturer": "Socionext", "component_type": "ic",
             "description": "HDMI transmitter/receiver chip", "notes": "Named in its own wiki section, \"HDMI Chip MN864739\"."},
            {"part_number": "AOZ1351DI-01", "manufacturer": "Alpha and Omega Semiconductor", "component_type": "ic",
             "description": "USB-PD/VBUS current-limiting protection IC, DFN12 package", "notes": "On the EDM-020 board revision."},
            {"part_number": "CX090061GG", "manufacturer": "Sony Interactive Entertainment", "component_type": "ic",
             "description": "EMI/RFI suppression IC", "notes": "On the EDM-010 board revision; several surrounding SMD components were knocked off and reverse-engineered for replacement during a repair."},
        ],
    },
    {
        "manufacturer": "Ramsey", "model_number": "STE-3000 Shielded Test Enclosure", "category": "test_equipment",
        "description": "A Faraday-cage test enclosure used to block electromagnetic fields around a device under test (DUT), with a viewing window and glove ports for hands-on interaction with the shielded DUT.",
        "teardown_notes": "Covers both an older revision (BNC/DB9 signal pass-throughs) and general construction: mesh/plexiglass viewing window, metal-mesh glove ports, and blade connectors for passing power into the shielded enclosure.",
        "source_url": "https://wiki.recessim.com/view/Ramsey_STE-3000_Shielded_Test_Enclosure",
        "images": [
            {"filename": "Ramsey-STE3000-1.jpeg", "caption": "Open Faraday cage", "type": "overview"},
            {"filename": "Ramsey-STE3000-2.jpeg", "caption": "Closed cage with mesh/plexiglass viewing window and glove ports", "type": "overview"},
            {"filename": "Ramsey-STE3000-3.jpeg", "caption": "BNC and DB9 signal pass-throughs (older unit)", "type": "ports"},
            {"filename": "Ramsey-STE3000-4.jpeg", "caption": "Internal view with glove ports", "type": "internal"},
        ],
        "components": [],
    },
    {
        "manufacturer": "Roland", "model_number": "DIF-AT", "category": "audio",
        "description": "A digital audio format interface/converter device supporting formats including Roland RBUS, Tascam T-DIF, and Alesis ADAT.",
        "teardown_notes": "In-depth reverse engineering: PCB photos and pinouts, a boundary-scan/BSDL investigation of the Xilinx CPLD, extraction of the firmware from a SHARP LH28F400BVE parallel NOR flash via a T48 programmer, Binwalk entropy analysis and disassembly in Ghidra/HEW/Cutter revealing a diagnostic routine and a DFU firmware-update routine, a Python DFU update script, and board-level repairs including trace repair around the H8/3005 CPU. A separate custom Alesis chip (handling all audio format I/O) could not be identified and is suspected to be an ASIC.",
        "source_url": "https://wiki.recessim.com/view/Roland_DIF-AT",
        "images": [
            {"filename": "DIF-AT MAIN.JPG", "caption": "Main board", "type": "pcb_top"},
            {"filename": "H8 3005 CPU.JPG", "caption": "H8/3005 CPU (not an MCU — no onboard JTAG)", "type": "closeup"},
            {"filename": "Xilinx CPLD.jpg", "caption": "Xilinx CPLD with JTAG pads visible", "type": "closeup"},
            {"filename": "SRAM + NOR FLASH.JPG", "caption": "SRAM and NOR flash (512kb)", "type": "closeup"},
        ],
        "components": [
            {"part_number": "H8/3005", "manufacturer": "Hitachi/Renesas", "component_type": "mcu",
             "description": "H8300H-family 16-bit CPU", "notes": "Main CPU; has no JTAG, only a bootloader boot mode."},
            {"part_number": "LH28F400BVE", "manufacturer": "Sharp", "component_type": "eeprom",
             "description": "16-bit-wide parallel NOR flash, 512kb, read in 8-bit mode", "notes": "Firmware storage; extracted via a T48 programmer for analysis."},
            {"part_number": "XC95144", "manufacturer": "Xilinx", "component_type": "ic",
             "description": "CPLD (XC9500 family)", "notes": "Handles RBUS signal routing; the only device on the JTAG chain."},
        ],
    },
    {
        "manufacturer": "Zimplistic", "model_number": "Rotimatic", "category": "kitchen",
        "description": "The Rotimatic is a robotic kitchen appliance that automatically measures, mixes, and kneads flour dough, then flattens and cooks it into rotis (flatbread) in about 90 seconds, coordinating 10 motors and 15 sensors via a 32-bit microcontroller.",
        "teardown_notes": "Documents extensive support-call troubleshooting alongside teardown photos of the main board, kicker/limit-switch assembly, load-cell mixer motor, flour/water/oil dispenser, capacitive-touch input board, and LCD.",
        "source_url": "https://wiki.recessim.com/view/Roti_making_robot_rotimatic",
        "images": [
            {"filename": "Roti rotimatic complete set.jpg", "caption": "Rotimatic, complete unit", "type": "overview"},
            {"filename": "Roti rotimatic main board PIC32MX470F512L.jpg", "caption": "Main board (PIC32MX470F512L)", "type": "pcb_top"},
            {"filename": "Roti rotimatic bluegiga WF121-A.jpg", "caption": "Bluegiga WF121-A Wi-Fi module", "type": "closeup"},
            {"filename": "Roti rotimatic capacitive touch PCB front.jpg", "caption": "Capacitive-touch input board", "type": "pcb_top"},
        ],
        "components": [
            {"part_number": "PIC32MX470F512L", "manufacturer": "Microchip Technology", "component_type": "mcu",
             "description": "32-bit MIPS32 M4K microcontroller, 80MHz, 512KB flash", "notes": "Main board controller."},
            {"part_number": "WF121-A", "manufacturer": "Silicon Labs (Bluegiga)", "component_type": "rf_module",
             "description": "Wi-Fi module", "notes": "Provides the device's Wi-Fi connectivity."},
            {"part_number": "P112-AL1-035", "manufacturer": "Soway", "component_type": "sensor",
             "description": "Magnetic reed switch sensor", "notes": "Used for a limit-switch/position-sensing function."},
        ],
    },
    {
        "manufacturer": "Unbranded/OEM", "model_number": "SQ11 Mini DV Camera", "category": "camera",
        "description": "A cheap, unbranded 23x23x23mm miniature spy/action camera sold widely under the \"SQ11\" name, recording to microSD in AVI format over a USB mini 8-pin port.",
        "teardown_notes": "The onboard SPI flash was identified as a Puya Semiconductor P25Q40H (4Mbit); the specific camera-module and secondary IC markings were not conclusively identified.",
        "source_url": "https://wiki.recessim.com/view/SQ11_mini_DV",
        "images": [
            {"filename": "2024-01-17-17-49-39-515.jpg", "caption": "SQ11 mini DV overview", "type": "overview"},
            {"filename": "2024-01-17-17-50-32-245.jpg", "caption": "Internal view", "type": "internal"},
            {"filename": "SQ11 port pinout.png", "caption": "USB port pinout", "type": "schematic"},
        ],
        "components": [
            {"part_number": "P25Q40H", "manufacturer": "Puya Semiconductor", "component_type": "eeprom",
             "description": "4Mbit SPI flash memory", "notes": "Firmware/storage flash."},
        ],
    },
    {
        "manufacturer": "Sangamo", "model_number": "FM2S", "category": "industrial",
        "description": "A Sangamo FM2S utility meter found at an antique store, initially mistaken for a purely analog electromechanical meter until disassembly revealed an internal PCB.",
        "teardown_notes": "Teardown photos of the meter's internals; specific ICs on the board have not yet been identified.",
        "source_url": "https://wiki.recessim.com/view/Sangamo_FM2S",
        "images": [
            {"filename": "Fm2s 001.jpg", "caption": "Sangamo FM2S — teardown photo 1", "type": "other"},
            {"filename": "Fm2s 006.jpg", "caption": "Sangamo FM2S — teardown photo 6", "type": "other"},
            {"filename": "Fm2s 010.jpg", "caption": "Sangamo FM2S — teardown photo 10", "type": "other"},
            {"filename": "Fm2s 014.jpg", "caption": "Sangamo FM2S — teardown photo 14", "type": "other"},
        ],
        "components": [],
    },
    {
        "manufacturer": "Starcom Systems", "model_number": "Helios", "category": "gps",
        "description": "A vehicle telematics/GPS tracking unit from Starcom Systems, combining cellular (UMTS/HSPA), GPS, and CAN-bus connectivity for fleet tracking.",
        "teardown_notes": "Parts list identified from datasheet-linked component markings, covering the cellular modem, GPS module, RS232/CAN transceivers, level shifting, SPI flash, a relay/solenoid driver, a switching regulator, a MOSFET, and the main ARM Cortex-M3 MCU.",
        "source_url": "https://wiki.recessim.com/view/Starcom_Helios",
        "images": [],
        "components": [
            {"part_number": "UG96", "manufacturer": "Quectel", "component_type": "rf_module",
             "description": "UMTS/HSPA 3G cellular module", "notes": "Cellular connectivity."},
            {"part_number": "L70R", "manufacturer": "Quectel", "component_type": "rf_module",
             "description": "GPS module", "notes": "Positioning."},
            {"part_number": "SN65C3221EPWR", "manufacturer": "Texas Instruments", "component_type": "ic",
             "description": "RS232 transceiver", "notes": ""},
            {"part_number": "SN74AVC4T774RGYR", "manufacturer": "Texas Instruments", "component_type": "ic",
             "description": "Level shifter / transceiver", "notes": ""},
            {"part_number": "W25Q16JVSIQ", "manufacturer": "Winbond", "component_type": "eeprom",
             "description": "16Mbit SPI NOR flash", "notes": ""},
            {"part_number": "ULN2003AI", "manufacturer": "Texas Instruments", "component_type": "ic",
             "description": "Darlington transistor array driver", "notes": ""},
            {"part_number": "LT8620", "manufacturer": "Analog Devices (Linear Technology)", "component_type": "regulator",
             "description": "Switching regulator", "notes": ""},
            {"part_number": "SN65HVD232Q", "manufacturer": "Texas Instruments", "component_type": "ic",
             "description": "CAN transceiver", "notes": "Marked HV230Q."},
            {"part_number": "UT4413G", "manufacturer": "Unisonic Technologies", "component_type": "mosfet",
             "description": "MOSFET", "notes": ""},
            {"part_number": "LPC1765FET100", "manufacturer": "NXP", "component_type": "mcu",
             "description": "ARM Cortex-M3 MCU, 256KB flash, 64KB SRAM", "notes": "Main controller."},
        ],
    },
    {
        "manufacturer": "Techem", "model_number": "FHKV data II", "category": "industrial",
        "description": "A heat-cost-allocation metering device commonly attached to individual radiators to measure and remotely report heat usage via RF.",
        "teardown_notes": "The main measurement IC's markings (\"9CCS4HT G4 M430U 300 RELEASE 4\") could not be matched to any public datasheet. Board measures at least two temperatures (radiator and ambient) and appears to include an inactive tampering-detection feature.",
        "source_url": "https://wiki.recessim.com/view/Techem_FHKV_data_II",
        "images": [
            {"filename": "Techem-fhkv-data-2-type-front.jpg", "caption": "Techem FHKV data II, front", "type": "overview"},
            {"filename": "Techem fhkv data 3 front pcb.jpg", "caption": "PCB, front", "type": "pcb_top"},
            {"filename": "Techem-fhkv-data-2-type-bottom.jpg", "caption": "Bottom of the device", "type": "other"},
        ],
        "components": [],
    },
    {
        "manufacturer": "Telematics Wireless", "model_number": "FP300RA", "category": "automotive",
        "description": "The FP-300RA is a roadside reader unit used in electronic Automatic Vehicle Identification (AVI) systems, such as toll collection.",
        "teardown_notes": "High-resolution PCB photos with the RF section's shielding can both in place and removed, plus case, connector, and RF-gasket detail shots.",
        "source_url": "https://wiki.recessim.com/view/Telematics_Wireless_FP300RA",
        "images": [
            {"filename": "TelematicsWireless FP300RA Overview.jpeg", "caption": "FP300RA overview", "type": "overview"},
            {"filename": "TelematicsWireless FP300RA PCBTop.jpg", "caption": "PCB top, RF shielding can removed", "type": "pcb_top"},
            {"filename": "TelematicsWireless FP300RA PCBBottom.jpg", "caption": "PCB bottom", "type": "pcb_bottom"},
            {"filename": "TelematicsWireless FP300RA ConnRF.JPG", "caption": "RF connections", "type": "ports"},
        ],
        "components": [],
    },
    {
        "manufacturer": "TomTom", "model_number": "BRIDGE 7\" Truck/Pro 8275 (4FI70)", "category": "gps",
        "description": "An Android-based, ruggedized commercial fleet/truck navigation and telematics tablet from TomTom's BRIDGE line, built around a Qualcomm Snapdragon 400 (quad-core, 1.2GHz) SoC.",
        "teardown_notes": "Documents an Android `createPackageContext` misuse research finding on this device's factory-tools/administration app, allowing a privilege-escalation proof-of-concept (broadcasting a MASTER_CLEAR intent via a debug intent sender) that was used to unlock the device's Factory Tools mode. Findings are written up in an accompanying research paper.",
        "source_url": "https://wiki.recessim.com/view/TomTom_BRIDGE_7\"_Truck/Pro_8275_(4FI70)",
        "images": [
            {"filename": "Tomtom0.png", "caption": "TomTom BRIDGE 7\" overview", "type": "overview"},
            {"filename": "Tomtom1.png", "caption": "TomTom BRIDGE 7\", additional view", "type": "other"},
            {"filename": "Factory tools.jpg", "caption": "Factory Tools mode, unlocked via the createPackageContext research finding", "type": "other"},
        ],
        "components": [
            {"part_number": "Snapdragon 400", "manufacturer": "Qualcomm", "component_type": "ic",
             "description": "Quad-core 1.2GHz applications processor", "notes": "Main SoC."},
        ],
    },
    {
        "manufacturer": "Topping", "model_number": "PA5", "category": "audio",
        "description": "A small, affordable Class-D stereo amplifier with a fully balanced pre- and post-amp section and two selectable inputs, well-regarded in the HiFi measurement community for exceptionally low noise floor and distortion.",
        "teardown_notes": "A major design flaw led to a high failure rate, which the manufacturer addressed by discontinuing this model in favor of the redesigned PA5 II. Failures center on the potted \"Topping D01\" module containing the preamp section; documents de-potting the module, dissecting its PCB, and multiple community-designed replacement modules (v1, v2, and a DIP-socketed version) with design files.",
        "source_url": "https://wiki.recessim.com/view/Topping_PA5",
        "images": [
            {"filename": "Topping PA5 Top Side No Heatsink.jpg", "caption": "PA5 top side, heatsink removed", "type": "pcb_top"},
            {"filename": "Topping PA5 Bottom Side PCB.jpg", "caption": "PA5 bottom side PCB", "type": "pcb_bottom"},
            {"filename": "Topping D01 Schematic.png", "caption": "Topping D01 module schematic (reverse-engineered)", "type": "schematic"},
        ],
        "components": [
            {"part_number": "TPA3251", "manufacturer": "Texas Instruments", "component_type": "ic",
             "description": "Class-D amplifier chip", "notes": "Main amplifier IC, running at approximately 36VDC."},
        ],
    },
    {
        "manufacturer": "Tytera", "model_number": "MD-380", "category": "radio",
        "description": "A DMR (Digital Mobile Radio) handheld transceiver, widely known in the amateur radio community for the MD380Tools/OpenGD77 custom firmware projects that unlock diagnostic features and modify its behavior.",
        "teardown_notes": "This wiki page is primarily a links/references collection pointing to the modified-firmware community projects rather than an original teardown.",
        "source_url": "https://wiki.recessim.com/view/Tytera_MD-380",
        "images": [
            {"filename": "Tytera MD-380.jpg", "caption": "Tytera MD-380", "type": "overview"},
        ],
        "components": [],
    },
    {
        "manufacturer": "Vaisala", "model_number": "RS41 Radiosonde", "category": "other",
        "description": "The Vaisala RS41 (SG and SGP variants) is a widely used balloon-launched radiosonde for meteorological sounding, transmitting sensor telemetry over radio.",
        "teardown_notes": "This wiki page is still a stub in progress; content so far covers the device's serial telemetry/configuration menu (test mode, sensor status, frequency, TX power) and a reverse-engineered register map for its Silicon Labs Si4030 sub-GHz transmitter, based on firmware version 2.02.15 (BETA). No photos have been uploaded to this page yet.",
        "source_url": "https://wiki.recessim.com/view/Vaisala_RS41_Radiosonde_Weather_Balloon_Sensor_Payload",
        "images": [],
        "components": [
            {"part_number": "Si4030", "manufacturer": "Silicon Labs", "component_type": "rf_module",
             "description": "Sub-GHz FSK transmitter", "notes": "Main RF transmitter; register map reverse-engineered from the RS41-SG/SGP firmware."},
        ],
    },
    {
        "manufacturer": "Videri", "model_number": "VQ Digital Canvas", "category": "monitor",
        "description": "The Videri VQ is a large-format (475.8mm square, 1920x1920) Wi-Fi/Bluetooth-connected digital art display (\"Digital Canvas\") running Android 6, marketed as the world's thinnest and lightest such display.",
        "teardown_notes": "PCB-level teardown identifying the main application processor module (DPC-450T), power management, display bridge, Wi-Fi/Bluetooth, and NFC subsystems.",
        "source_url": "https://wiki.recessim.com/view/Videri",
        "images": [
            {"filename": "Videri VQ DPC-450T PCB CPU eMMC SD WiFi BlueTooth Connectors.jpg", "caption": "DPC-450T processor PCB with eMMC, SD, Wi-Fi/Bluetooth connectors", "type": "pcb_top"},
            {"filename": "Videri VQ Qualcomm PM8994 Power Management IC.jpg", "caption": "Qualcomm PM8994 power management IC", "type": "closeup"},
            {"filename": "Videri VQ CHRONTEL CH7515A TF.jpg", "caption": "Chrontel CH7515A display bridge", "type": "closeup"},
            {"filename": "Videri VQ TI TPS54427 Buck Regulator.jpg", "caption": "TI TPS54427 buck regulator", "type": "closeup"},
        ],
        "components": [
            {"part_number": "PM8994", "manufacturer": "Qualcomm", "component_type": "ic",
             "description": "Power management IC", "notes": ""},
            {"part_number": "CH7515A", "manufacturer": "Chrontel", "component_type": "ic",
             "description": "eDP/LVDS display bridge", "notes": ""},
            {"part_number": "TPS54427", "manufacturer": "Texas Instruments", "component_type": "regulator",
             "description": "Buck regulator", "notes": ""},
            {"part_number": "QCNFA324", "manufacturer": "Qualcomm", "component_type": "rf_module",
             "description": "Wi-Fi/Bluetooth combo module (marked PPD-QCNFA324)", "notes": "FCC ID PPD-QCNFA324."},
        ],
    },
    {
        "manufacturer": "Yaesu", "model_number": "FT2DR", "category": "radio",
        "description": "A dual-band handheld amateur radio transceiver with built-in APRS/GPS from Yaesu's FT2D series.",
        "teardown_notes": "Full teardown video and photo set covering the case, chassis, screen, processor board, and RF board (top and bottom of each).",
        "source_url": "https://wiki.recessim.com/view/Yaesu_FT2DR",
        "images": [
            {"filename": "Yaesu FT2DR Fully Disassembled.jpeg", "caption": "Yaesu FT2DR, fully disassembled", "type": "overview"},
            {"filename": "Yaesu FT2DR Processor Top.JPG", "caption": "Processor board, top", "type": "pcb_top"},
            {"filename": "Yaesu FT2DR Processor Bottom 1.JPG", "caption": "Processor board, bottom", "type": "pcb_bottom"},
            {"filename": "Yaesu FT2DR RF Top 1.JPG", "caption": "RF board, top", "type": "pcb_top"},
        ],
        "components": [],
    },
    {
        "manufacturer": "Yaesu", "model_number": "FT3DR", "category": "radio",
        "description": "A dual-band handheld amateur radio transceiver with built-in APRS/GPS from Yaesu's FT3D series.",
        "teardown_notes": "Full teardown video and photo set covering the case, speaker, chassis, processor board, RF board, screen, and GPS antenna selector assembly.",
        "source_url": "https://wiki.recessim.com/view/Yaesu_FT3DR",
        "images": [
            {"filename": "Yaesu FT3DR Teardown Picture.jpeg", "caption": "Yaesu FT3DR, teardown overview", "type": "overview"},
            {"filename": "Yaesu FT3DR Processor Top.JPG", "caption": "Processor board, top", "type": "pcb_top"},
            {"filename": "Yaesu FT3DR Processor Bottom.JPG", "caption": "Processor board, bottom", "type": "pcb_bottom"},
            {"filename": "Yaesu FT3DR RF Top.JPG", "caption": "RF board, top", "type": "pcb_top"},
        ],
        "components": [],
    },
]


class Command(BaseCommand):
    help = "Import curated product teardown documentation from the RECESSIM wiki (CC BY-SA 4.0)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing recessim-sourced products (by manufacturer/model) before re-importing.",
        )

    def handle(self, *args, **options):
        admin = User.objects.filter(is_superuser=True).order_by("date_joined").first()
        if not admin:
            self.stderr.write(self.style.ERROR("No admin user found. Run seed_data first."))
            return

        created_products = 0
        skipped_products = 0
        failed_products = []
        created_images = 0
        failed_images = 0
        created_components = 0

        for entry in PRODUCTS:
            manufacturer = entry["manufacturer"]
            model_number = entry["model_number"]
            try:
                if options["flush"]:
                    Product.objects.filter(
                        manufacturer=manufacturer, model_number=model_number,
                        revision="", region="global",
                    ).delete()

                teardown_notes = entry.get("teardown_notes", "").strip()
                attribution = (
                    f"Teardown documentation and photography sourced from the RECESSIM wiki "
                    f"({entry['source_url']}), licensed CC BY-SA 4.0."
                )
                full_notes = f"{teardown_notes}\n\n{attribution}" if teardown_notes else attribution

                product, made = Product.objects.get_or_create(
                    manufacturer=manufacturer, model_number=model_number,
                    revision="", region="global",
                    defaults=dict(
                        category=entry["category"],
                        description=entry.get("description", ""),
                        teardown_notes=full_notes,
                        source_url=entry["source_url"],
                        created_by=admin,
                        is_approved=True,
                    ),
                )
                if not made:
                    skipped_products += 1
                    continue
                created_products += 1
                self.stdout.write(f"Created: {product}")

                for img in entry.get("images", []):
                    try:
                        data = fetch_wiki_file_bytes(img["filename"])
                        pi = ProductImage(
                            product=product,
                            image_type=img["type"],
                            caption=img.get("caption", ""),
                            uploaded_by=admin,
                            is_approved=True,
                        )
                        pi.image.save(img["filename"], ContentFile(data), save=False)
                        pi.save()
                        created_images += 1
                    except Exception as e:
                        failed_images += 1
                        self.stderr.write(self.style.WARNING(
                            f"  image failed for {manufacturer} {model_number} / {img['filename']}: {e}"
                        ))

                for comp in entry.get("components", []):
                    component, _ = Component.objects.get_or_create(
                        manufacturer=comp["manufacturer"],
                        part_number=comp["part_number"],
                        defaults=dict(
                            component_type=comp["component_type"],
                            description=comp.get("description", ""),
                            created_by=admin,
                        ),
                    )
                    _, comp_made = ProductComponent.objects.get_or_create(
                        product=product, component=component,
                        defaults=dict(
                            reference_designator=comp.get("reference_designator", ""),
                            quantity=comp.get("quantity", 1),
                            notes=comp.get("notes", ""),
                            created_by=admin,
                        ),
                    )
                    if comp_made:
                        created_components += 1
            except Exception as e:
                failed_products.append((manufacturer, model_number, str(e)))
                self.stderr.write(self.style.ERROR(f"FAILED {manufacturer} {model_number}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nProducts: {created_products} created, {skipped_products} skipped (already existed), "
            f"{len(failed_products)} failed.\n"
            f"Images: {created_images} created, {failed_images} failed.\n"
            f"Components linked: {created_components}."
        ))
        for m, mo, err in failed_products:
            self.stdout.write(self.style.WARNING(f"  FAILED: {m} {mo}: {err}"))
