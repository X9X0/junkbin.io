"""
Unit tests for apps.components.value_search.
"""
import pytest

from apps.components.value_search import parse_value_query, spec_key_candidates


def assert_parsed(query, kind, magnitude):
    result = parse_value_query(query)
    assert result is not None, f'{query!r} failed to parse'
    parsed_kind, parsed_magnitude = result
    assert parsed_kind == kind
    assert parsed_magnitude == pytest.approx(magnitude)


class TestParseValueQueryResistance:
    def test_bare_kilo(self):
        assert_parsed('10k', 'resistance', 10_000.0)

    def test_bare_kilo_uppercase(self):
        assert_parsed('4.7K', 'resistance', 4_700.0)

    def test_bare_mega(self):
        assert_parsed('1M', 'resistance', 1_000_000.0)

    def test_bare_no_prefix(self):
        assert_parsed('220', 'resistance', 220.0)

    def test_explicit_ohm_symbol(self):
        assert_parsed('220Ω', 'resistance', 220.0)

    def test_explicit_ohm_word(self):
        assert_parsed('220ohm', 'resistance', 220.0)

    def test_explicit_r_suffix(self):
        assert_parsed('10R', 'resistance', 10.0)

    def test_kilo_ohm_explicit(self):
        assert_parsed('10kΩ', 'resistance', 10_000.0)


class TestParseValueQueryCapacitance:
    def test_bare_nano(self):
        assert_parsed('100n', 'capacitance', 1e-7)

    def test_bare_micro(self):
        assert_parsed('4.7u', 'capacitance', 4.7e-6)

    def test_bare_micro_symbol(self):
        assert_parsed('4.7µ', 'capacitance', 4.7e-6)

    def test_bare_pico(self):
        assert_parsed('220p', 'capacitance', 220e-12)

    def test_explicit_nf(self):
        assert_parsed('100nF', 'capacitance', 1e-7)

    def test_explicit_uf(self):
        assert_parsed('4.7uF', 'capacitance', 4.7e-6)


class TestParseValueQueryInductance:
    def test_bare_milli(self):
        assert_parsed('2.2m', 'inductance', 2.2e-3)

    def test_explicit_mh(self):
        assert_parsed('2.2mH', 'inductance', 2.2e-3)

    def test_explicit_uh(self):
        assert_parsed('10uH', 'inductance', 10e-6)


class TestParseValueQueryFrequency:
    def test_explicit_mhz(self):
        assert_parsed('16MHz', 'frequency', 16_000_000.0)

    def test_explicit_ghz(self):
        assert_parsed('2.4GHz', 'frequency', 2_400_000_000.0)

    def test_explicit_khz(self):
        assert_parsed('32.768kHz', 'frequency', 32_768.0)

    def test_bare_giga_is_frequency(self):
        assert_parsed('2.4G', 'frequency', 2_400_000_000.0)


class TestParseValueQueryVoltageAndCurrent:
    def test_explicit_volts(self):
        assert_parsed('3.3V', 'voltage', 3.3)

    def test_explicit_milliamps(self):
        assert_parsed('500mA', 'current', 0.5)

    def test_explicit_amps(self):
        assert_parsed('2A', 'current', 2.0)


class TestParseValueQueryRejectsGarbage:
    def test_empty_string(self):
        assert parse_value_query('') is None

    def test_no_leading_number(self):
        assert parse_value_query('resistor') is None

    def test_unrecognized_unit(self):
        assert parse_value_query('10 pin') is None

    def test_malformed_embedded_digits(self):
        assert parse_value_query('10k5') is None

    def test_sentence(self):
        assert parse_value_query('10k ohm resistor') is None


class TestSpecKeyCandidates:
    def test_resistance_single_key_within_tolerance(self):
        candidates = spec_key_candidates('resistance', 10_000.0)
        assert len(candidates) == 1
        key, lo, hi = candidates[0]
        assert key == 'resistance_ohm'
        assert lo < 10_000.0 < hi

    def test_capacitance_covers_all_stored_units(self):
        candidates = spec_key_candidates('capacitance', 100e-9)  # 100nF
        keys = {key for key, _, _ in candidates}
        assert keys == {'capacitance_nf', 'capacitance_pf', 'capacitance_uf'}
        by_key = {key: (lo, hi) for key, lo, hi in candidates}
        lo, hi = by_key['capacitance_nf']
        assert lo < 100.0 < hi

    def test_unknown_kind_yields_no_candidates(self):
        assert spec_key_candidates('nonsense', 1.0) == []
