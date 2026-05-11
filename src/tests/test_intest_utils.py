"""Tests for state/FIPS/WQP code lookups."""

import pytest

from hydroflow.ingest_utils import (
    US_STATE_FIPS_TABLE,
    get_fips_from_state,
    get_state_from_fips,
    get_state_from_wqp,
    get_wqp_code,
)


class TestGetWqpCode:
    def test_exact_match(self):
        assert get_wqp_code("Washington") == "US:53"

    def test_case_insensitive(self):
        assert get_wqp_code("washington") == "US:53"
        assert get_wqp_code("WASHINGTON") == "US:53"
        assert get_wqp_code("wAsHiNgToN") == "US:53"

    def test_whitespace_tolerant(self):
        assert get_wqp_code("  Washington  ") == "US:53"
        assert get_wqp_code("\tArizona\n") == "US:04"

    def test_multiword_state(self):
        assert get_wqp_code("New York") == "US:36"
        assert get_wqp_code("North Carolina") == "US:37"
        assert get_wqp_code("District of Columbia") == "US:11"

    def test_territory(self):
        assert get_wqp_code("Puerto Rico") == "US:72"
        assert get_wqp_code("Guam") == "US:66"

    def test_unknown_state_returns_none(self):
        assert get_wqp_code("Atlantis") is None
        assert get_wqp_code("") is None

    def test_partial_match_not_accepted(self):
        # Defensive: 'Wash' should not match 'Washington'.
        assert get_wqp_code("Wash") is None


class TestGetStateFromWqp:
    def test_basic(self):
        assert get_state_from_wqp("US:53") == "Washington"

    def test_case_insensitive(self):
        assert get_state_from_wqp("us:53") == "Washington"

    def test_unknown_returns_none(self):
        assert get_state_from_wqp("US:99") is None


class TestGetFipsFromState:
    def test_basic(self):
        assert get_fips_from_state("Washington") == "53"

    def test_leading_zero_preserved(self):
        # FIPS codes are 2-digit zero-padded strings.
        assert get_fips_from_state("Alabama") == "01"
        assert get_fips_from_state("Connecticut") == "09"

    def test_unknown_returns_none(self):
        assert get_fips_from_state("Atlantis") is None


class TestGetStateFromFips:
    def test_basic(self):
        assert get_state_from_fips("53") == "Washington"

    def test_accepts_int(self):
        assert get_state_from_fips(53) == "Washington"

    def test_pads_single_digit(self):
        # '1' should be treated as '01'.
        assert get_state_from_fips("1") == "Alabama"
        assert get_state_from_fips(1) == "Alabama"

    def test_unknown_returns_none(self):
        assert get_state_from_fips("99") is None


class TestTableIntegrity:
    """Guards against accidental edits to US_STATE_FIPS_TABLE."""

    def test_no_duplicate_state_names(self):
        names = [row["state_name"] for row in US_STATE_FIPS_TABLE]
        assert len(names) == len(set(names))

    def test_no_duplicate_fips_codes(self):
        codes = [row["fips_code"] for row in US_STATE_FIPS_TABLE]
        assert len(codes) == len(set(codes))

    def test_no_duplicate_wqp_codes(self):
        codes = [row["wqp_code"] for row in US_STATE_FIPS_TABLE]
        assert len(codes) == len(set(codes))

    def test_wqp_code_matches_fips(self):
        # wqp_code should always be 'US:' + fips_code.
        for row in US_STATE_FIPS_TABLE:
            assert row["wqp_code"] == f"US:{row['fips_code']}", row

    def test_fips_codes_are_two_digits(self):
        for row in US_STATE_FIPS_TABLE:
            assert len(row["fips_code"]) == 2, row
            assert row["fips_code"].isdigit(), row

    @pytest.mark.parametrize(
        "state,expected_wqp",
        [
            ("Washington", "US:53"),
            ("Arizona", "US:04"),
            ("New York", "US:36"),
            ("Puerto Rico", "US:72"),
        ],
    )
    def test_roundtrip(self, state, expected_wqp):
        assert get_wqp_code(state) == expected_wqp
        assert get_state_from_wqp(expected_wqp) == state
