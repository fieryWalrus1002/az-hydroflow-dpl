"""Tests for Pydantic param models."""

from datetime import date

import pytest
from pydantic import ValidationError

from hydroflow.wqp_params import WQPResultsParams, WQPSiteQueryParams


# ---------------------------------------------------------------------------
# WQPSiteQueryParams
# ---------------------------------------------------------------------------

class TestWQPSiteQueryParamsConstruction:
    def test_minimal_valid(self):
        p = WQPSiteQueryParams(state_name="Washington")
        assert p.state_name == "Washington"
        assert p.site_type == "Stream"  # default
        assert p.characteristic_name is None
        assert p.characteristic_type is None
        assert p.providers is None

    def test_full_construction(self):
        p = WQPSiteQueryParams(
            state_name="Arizona",
            site_type=["Stream", "Lake, Reservoir, Impoundment"],
            characteristic_name=["Nitrate", "Phosphorus"],
            providers=["NWIS", "STORET"],
        )
        assert p.state_name == "Arizona"
        assert p.site_type == ["Stream", "Lake, Reservoir, Impoundment"]
        assert p.characteristic_name == ["Nitrate", "Phosphorus"]
        assert p.providers == ["NWIS", "STORET"]

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            WQPSiteQueryParams(state_name="Washington", typo_field="oops")

    def test_frozen(self):
        p = WQPSiteQueryParams(state_name="Washington")
        with pytest.raises(ValidationError):
            p.state_name = "Arizona"  # type: ignore[misc]


class TestWQPSiteQueryParamsStateValidation:
    def test_unknown_state_rejected(self):
        with pytest.raises(ValidationError, match="Unknown state or territory"):
            WQPSiteQueryParams(state_name="Atlantis")

    def test_empty_state_rejected(self):
        with pytest.raises(ValidationError):
            WQPSiteQueryParams(state_name="")

    def test_state_case_insensitive(self):
        # The lookup is case-insensitive, so this should validate.
        p = WQPSiteQueryParams(state_name="washington")
        assert p.wqp_statecode == "US:53"


class TestWQPSiteQueryParamsCharacteristicExclusion:
    def test_both_characteristic_fields_rejected(self):
        with pytest.raises(ValidationError, match="should not be combined"):
            WQPSiteQueryParams(
                state_name="Washington",
                characteristic_name="Nitrate",
                characteristic_type="Nutrient",
            )

    def test_only_name_ok(self):
        p = WQPSiteQueryParams(state_name="Washington", characteristic_name="Nitrate")
        assert p.characteristic_name == "Nitrate"
        assert p.characteristic_type is None

    def test_only_type_ok(self):
        p = WQPSiteQueryParams(state_name="Washington", characteristic_type="Nutrient")
        assert p.characteristic_type == "Nutrient"
        assert p.characteristic_name is None


class TestWQPSiteQueryParamsEmptyStringRejection:
    def test_empty_site_type_string_rejected(self):
        with pytest.raises(ValidationError):
            WQPSiteQueryParams(state_name="Washington", site_type="")

    def test_empty_in_list_rejected(self):
        with pytest.raises(ValidationError):
            WQPSiteQueryParams(state_name="Washington", site_type=["Stream", ""])

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValidationError):
            WQPSiteQueryParams(state_name="Washington", characteristic_name="   ")


class TestWQPSiteQueryParamsProviders:
    def test_invalid_provider_rejected(self):
        with pytest.raises(ValidationError):
            WQPSiteQueryParams(state_name="Washington", providers=["WRONG"])

    def test_valid_providers(self):
        p = WQPSiteQueryParams(state_name="Washington", providers=["NWIS"])
        assert p.providers == ["NWIS"]


class TestWQPSiteQueryParamsToKwargs:
    def test_minimal(self):
        p = WQPSiteQueryParams(state_name="Washington")
        assert p.to_wqp_kwargs() == {
            "statecode": "US:53",
            "siteType": "Stream",
        }

    def test_multiple_site_types_joined_with_semicolons(self):
        p = WQPSiteQueryParams(
            state_name="Washington",
            site_type=["Stream", "Lake, Reservoir, Impoundment"],
        )
        kw = p.to_wqp_kwargs()
        assert kw["siteType"] == "Stream;Lake, Reservoir, Impoundment"

    def test_characteristic_name_included(self):
        p = WQPSiteQueryParams(
            state_name="Washington",
            characteristic_name=["Nitrate", "Phosphorus"],
        )
        kw = p.to_wqp_kwargs()
        assert kw["characteristicName"] == "Nitrate;Phosphorus"
        assert "characteristicType" not in kw

    def test_providers_joined(self):
        p = WQPSiteQueryParams(state_name="Washington", providers=["NWIS", "STORET"])
        kw = p.to_wqp_kwargs()
        assert kw["providers"] == "NWIS;STORET"

    def test_none_fields_omitted(self):
        p = WQPSiteQueryParams(state_name="Washington")
        kw = p.to_wqp_kwargs()
        assert "characteristicName" not in kw
        assert "characteristicType" not in kw
        assert "providers" not in kw

    def test_case_preserved(self):
        """WQP API is case-sensitive for site_type and characteristic values."""
        p = WQPSiteQueryParams(
            state_name="Washington",
            site_type="Stream",
            characteristic_name="Atrazine",
        )
        kw = p.to_wqp_kwargs()
        assert kw["siteType"] == "Stream"  # not 'stream'
        assert kw["characteristicName"] == "Atrazine"


class TestWQPSiteQueryParamsSlug:
    def test_basic(self):
        p = WQPSiteQueryParams(state_name="Washington")
        assert p.slug() == "washington_stream"

    def test_multiword_state(self):
        p = WQPSiteQueryParams(state_name="New York")
        assert p.slug() == "new_york_stream"

    def test_multiple_site_types(self):
        p = WQPSiteQueryParams(state_name="Arizona", site_type=["Stream", "Spring"])
        assert p.slug() == "arizona_stream-spring"


class TestWQPSiteQueryParamsStatecodeProperty:
    def test_resolved_correctly(self):
        p = WQPSiteQueryParams(state_name="Arizona")
        assert p.wqp_statecode == "US:04"


# ---------------------------------------------------------------------------
# WQPResultsParams
# ---------------------------------------------------------------------------

class TestWQPResultsParamsConstruction:
    def test_minimal_valid(self):
        p = WQPResultsParams(site_id="USGS-12345678")
        assert p.site_id == "USGS-12345678"
        assert p.start_date is None
        assert p.end_date is None

    def test_with_dates(self):
        p = WQPResultsParams(
            site_id="USGS-12345678",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )
        assert p.start_date == date(2020, 1, 1)
        assert p.end_date == date(2020, 12, 31)

    def test_date_string_parsed(self):
        # Pydantic accepts ISO date strings.
        p = WQPResultsParams(site_id="USGS-12345678", start_date="2020-01-01")
        assert p.start_date == date(2020, 1, 1)

    def test_invalid_date_string_rejected(self):
        with pytest.raises(ValidationError):
            WQPResultsParams(site_id="USGS-12345678", start_date="not-a-date")

    def test_missing_site_id(self):
        with pytest.raises(ValidationError):
            WQPResultsParams()  # type: ignore[call-arg]

    def test_empty_site_id_rejected(self):
        with pytest.raises(ValidationError):
            WQPResultsParams(site_id="")


class TestWQPResultsParamsDateOrdering:
    def test_end_before_start_rejected(self):
        with pytest.raises(ValidationError, match="end_date must be on or after start_date"):
            WQPResultsParams(
                site_id="USGS-12345678",
                start_date=date(2020, 6, 1),
                end_date=date(2020, 1, 1),
            )

    def test_equal_dates_ok(self):
        p = WQPResultsParams(
            site_id="USGS-12345678",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 1),
        )
        assert p.start_date == p.end_date

    def test_only_start_ok(self):
        p = WQPResultsParams(site_id="USGS-12345678", start_date=date(2020, 1, 1))
        assert p.end_date is None

    def test_only_end_ok(self):
        p = WQPResultsParams(site_id="USGS-12345678", end_date=date(2020, 12, 31))
        assert p.start_date is None


class TestWQPResultsParamsToKwargs:
    def test_minimal(self):
        p = WQPResultsParams(site_id="USGS-12345678")
        assert p.to_wqp_kwargs() == {"siteid": "USGS-12345678"}

    def test_multiple_site_ids(self):
        p = WQPResultsParams(site_id=["USGS-1", "USGS-2"])
        assert p.to_wqp_kwargs() == {"siteid": "USGS-1;USGS-2"}

    def test_dates_formatted_as_mm_dd_yyyy(self):
        """WQP expects MM-DD-YYYY, not the more usual YYYY-MM-DD."""
        p = WQPResultsParams(
            site_id="USGS-12345678",
            start_date=date(2020, 1, 5),
            end_date=date(2020, 12, 31),
        )
        kw = p.to_wqp_kwargs()
        assert kw["startDateLo"] == "01-05-2020"
        assert kw["startDateHi"] == "12-31-2020"

    def test_dates_zero_padded(self):
        p = WQPResultsParams(site_id="x", start_date=date(2020, 3, 7))
        assert p.to_wqp_kwargs()["startDateLo"] == "03-07-2020"

    def test_characteristic_name(self):
        p = WQPResultsParams(site_id="x", characteristic_name=["Nitrate", "Phosphorus"])
        kw = p.to_wqp_kwargs()
        assert kw["characteristicName"] == "Nitrate;Phosphorus"


class TestWQPResultsParamsCharacteristicExclusion:
    def test_both_rejected(self):
        with pytest.raises(ValidationError, match="should not be combined"):
            WQPResultsParams(
                site_id="x",
                characteristic_name="Nitrate",
                characteristic_type="Nutrient",
            )
