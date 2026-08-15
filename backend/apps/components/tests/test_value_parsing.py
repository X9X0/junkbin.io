"""
Unit tests for apps.components.value_parsing.

Cases are drawn from real OCR'd service-manual BOM text (Sony PVM-14M2 and
Panasonic AG-MX70 product pages), including the garbled/split-token forms
that OCR reliably produces.
"""
from apps.components.value_parsing import (
    parse_capacitor_nf,
    parse_inductor_uh,
    parse_resistor_ohms,
)


class TestParseResistorOhms:
    def test_bare_ohms(self):
        assert parse_resistor_ohms('METAL GLAZE 120 5% | 1/10W') == 120.0

    def test_kilo_suffix(self):
        assert parse_resistor_ohms('METAL GLAZE 4.7K 5% | 1/10W') == 4700.0

    def test_mega_suffix(self):
        assert parse_resistor_ohms('METAL GLAZE 3.3M 5% | 1/10W') == 3_300_000.0

    def test_sub_ohm_value(self):
        assert parse_resistor_ohms('METAL OXIDE 0.68 5% | F 3W') == 0.68

    def test_ignores_tolerance_token(self):
        assert parse_resistor_ohms('METAL CHIP 100K 0.50% | 1/10W') == 100_000.0

    def test_ignores_bleed_after_pipe(self):
        notes = '51K METAL CHIP 0.50% | 1/10W Rl126 1-216-041-00 METALGLAZE 470 5%'
        assert parse_resistor_ohms(notes) == 51_000.0

    def test_split_tolerance_percent_not_mistaken_for_value(self):
        # OCR split "1%" into a standalone "%" and "1" token - the real
        # value (470) must win, not the stray "1".
        assert parse_resistor_ohms('% 1 CARBON 470 | 1/4W F') == 470.0

    def test_split_km_suffix_reglued(self):
        # OCR split "1K" into "1" and "K" tokens.
        assert parse_resistor_ohms('MET AL GLAZE 1 K 5%') == 1000.0

    def test_ocr_digit_repair(self):
        # "!0K" -> "10K" (! misread of 1)
        assert parse_resistor_ohms('METAL CHIP !0K 0.50%') == 10_000.0

    def test_unparseable_returns_none(self):
        assert parse_resistor_ohms('SCREW +P 3X10') is None
        assert parse_resistor_ohms('SOLID 20%') is None


class TestParseCapacitorNf:
    def test_picofarad_converts_to_nanofarad(self):
        assert parse_capacitor_nf('5% CERAMIC CHIP 470PF | 50V') == 0.47

    def test_microfarad_notation_converts_to_nanofarad(self):
        # Sony manuals use "MF" for microfarads.
        assert parse_capacitor_nf('ELECT 220MF 20% | 16V') == 220_000.0

    def test_sub_picofarad_precision(self):
        assert parse_capacitor_nf('CERAMIC CHIP 1PF 0.25PF | 50V') == 0.001

    def test_ignores_bleed_after_pipe(self):
        notes = '5% CERAMIC 100PF | 8.2K 5% 50V R7l6 J-216-486-00 METAL OXIDE'
        assert parse_capacitor_nf(notes) == 0.1

    def test_ocr_digit_repair(self):
        # "ISOPF" -> "150PF" (I/S/O misread of 1/5/0)
        assert parse_capacitor_nf('5% CERAMIC ISOPF | 15K 50V') == 0.15

    def test_unparseable_returns_none(self):
        assert parse_capacitor_nf('CERAMIC CHIP 0.1 MF | 25V <COMPOSITION CIRCUIT BLOCK>') is None


class TestParseInductorUh:
    def test_microhenry(self):
        assert parse_inductor_uh('INDUCTOR 33UH') == 33.0

    def test_millihenry_converts_to_microhenry(self):
        assert parse_inductor_uh('INDUCTOR 18mH') == 18_000.0

    def test_sub_microhenry(self):
        assert parse_inductor_uh('FERRITE BEAD INDUCTOR 0.45UH') == 0.45

    def test_ocr_digit_repair(self):
        # "lmH" -> "1mH" (l misread of 1)
        assert parse_inductor_uh('INDUCTOR lmH') == 1_000.0

    def test_unparseable_returns_none(self):
        assert parse_inductor_uh('TRAP, LC') is None
        assert parse_inductor_uh('COIL, CHOKE') is None
