"""Tests for ingest_wqp.

The network calls (``wqp.what_sites``, ``wqp.get_results``) are mocked
at the module-import path so the tests run offline.
"""

from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from hydroflow import ingest_wqp
from hydroflow.ingest_wqp import (
    build_query_metadata,
    get_bronze_path,
    get_raw_path,
    ingest_wqp_site_data,
    ingest_wqp_site_results,
    save_data_to_bronze,
    save_data_to_raw,
)
from hydroflow.wqp_params import WQPResultsParams, WQPSiteQueryParams


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def site_params():
    return WQPSiteQueryParams(state_name="Washington", site_type="Stream")


@pytest.fixture
def results_params():
    return WQPResultsParams(
        site_id="USGS-12345678",
        start_date=date(2020, 1, 1),
        end_date=date(2020, 12, 31),
    )


@pytest.fixture
def fake_sites_df():
    return pd.DataFrame(
        {
            "MonitoringLocationIdentifier": ["USGS-1", "USGS-2", "USGS-3"],
            "MonitoringLocationName": ["Site A", "Site B", "Site C"],
            "LatitudeMeasure": [47.6, 48.0, 46.5],
            "LongitudeMeasure": [-122.3, -121.5, -123.0],
        }
    )


@pytest.fixture
def fake_results_df():
    return pd.DataFrame(
        {
            "MonitoringLocationIdentifier": ["USGS-1", "USGS-1"],
            "ActivityStartDate": ["2020-03-15", "2020-06-20"],
            "CharacteristicName": ["Nitrate", "Phosphorus"],
            "ResultMeasureValue": [1.2, 0.05],
        }
    )


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

class TestPaths:
    def test_raw_path_default_dir(self, site_params):
        assert get_raw_path(site_params) == "data/raw/washington_stream_sites.csv"

    def test_bronze_path_default_dir(self, site_params):
        assert get_bronze_path(site_params) == "data/bronze/washington_stream_sites.parquet"

    def test_raw_path_custom_dir(self, site_params, tmp_path):
        assert get_raw_path(site_params, base_dir=str(tmp_path)) == f"{tmp_path}/washington_stream_sites.csv"

    def test_multiword_state_path(self):
        p = WQPSiteQueryParams(state_name="New York", site_type="Stream")
        assert get_raw_path(p) == "data/raw/new_york_stream_sites.csv"


# ---------------------------------------------------------------------------
# Persistence (uses tmp_path — real disk I/O, no mocks needed)
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_raw_writes_csv(self, site_params, fake_sites_df, tmp_path):
        path = save_data_to_raw(fake_sites_df, site_params, base_dir=str(tmp_path))
        assert path == f"{tmp_path}/washington_stream_sites.csv"
        roundtripped = pd.read_csv(path)
        pd.testing.assert_frame_equal(roundtripped, fake_sites_df)

    def test_save_bronze_writes_parquet(self, site_params, fake_sites_df, tmp_path):
        path = save_data_to_bronze(fake_sites_df, site_params, base_dir=str(tmp_path))
        assert path == f"{tmp_path}/washington_stream_sites.parquet"
        roundtripped = pd.read_parquet(path)
        pd.testing.assert_frame_equal(roundtripped, fake_sites_df)

    def test_save_raw_creates_missing_dirs(self, site_params, fake_sites_df, tmp_path):
        nested = tmp_path / "nested" / "deeper"
        save_data_to_raw(fake_sites_df, site_params, base_dir=str(nested))
        assert (nested / "washington_stream_sites.csv").exists()


# ---------------------------------------------------------------------------
# Metadata envelope
# ---------------------------------------------------------------------------

class TestBuildQueryMetadata:
    def test_includes_required_keys(self, site_params):
        meta = build_query_metadata(site_params, row_count=42, source_metadata={"upstream": "ok"})
        assert set(meta.keys()) == {
            "ingested_at_utc",
            "query_params",
            "wqp_kwargs",
            "row_count",
            "source_metadata",
        }

    def test_row_count_passed_through(self, site_params):
        meta = build_query_metadata(site_params, row_count=42)
        assert meta["row_count"] == 42

    def test_query_params_serialized_as_json_safe(self, results_params):
        # mode='json' should turn date objects into ISO strings.
        meta = build_query_metadata(results_params, row_count=0)
        assert meta["query_params"]["start_date"] == "2020-01-01"

    def test_wqp_kwargs_use_api_format(self, results_params):
        """The kwargs in metadata should use the API's MM-DD-YYYY format."""
        meta = build_query_metadata(results_params, row_count=0)
        assert meta["wqp_kwargs"]["startDateLo"] == "01-01-2020"

    def test_timestamp_is_utc_iso(self, site_params):
        meta = build_query_metadata(site_params, row_count=0)
        # Should parse cleanly as ISO with timezone.
        from datetime import datetime
        parsed = datetime.fromisoformat(meta["ingested_at_utc"])
        assert parsed.tzinfo is not None


# ---------------------------------------------------------------------------
# Orchestrators (network mocked)
# ---------------------------------------------------------------------------

class TestIngestWqpSiteData:
    def test_calls_wqp_with_correct_kwargs(self, site_params, fake_sites_df):
        with patch.object(ingest_wqp.wqp, "what_sites") as mock_what_sites:
            mock_what_sites.return_value = (fake_sites_df, {"upstream": "metadata"})

            df, meta = ingest_wqp_site_data(site_params)

            mock_what_sites.assert_called_once_with(
                statecode="US:53",
                siteType="Stream",
            )
            pd.testing.assert_frame_equal(df, fake_sites_df)

    def test_metadata_includes_upstream(self, site_params, fake_sites_df):
        with patch.object(ingest_wqp.wqp, "what_sites") as mock_what_sites:
            mock_what_sites.return_value = (fake_sites_df, {"upstream": "metadata"})
            _, meta = ingest_wqp_site_data(site_params)
            assert meta["source_metadata"] == {"upstream": "metadata"}
            assert meta["row_count"] == 3

    def test_passes_through_characteristic_name(self, fake_sites_df):
        params = WQPSiteQueryParams(
            state_name="Arizona",
            site_type="Stream",
            characteristic_name=["Nitrate", "Phosphorus"],
        )
        with patch.object(ingest_wqp.wqp, "what_sites") as mock_what_sites:
            mock_what_sites.return_value = (fake_sites_df, {})
            ingest_wqp_site_data(params)
            mock_what_sites.assert_called_once_with(
                statecode="US:04",
                siteType="Stream",
                characteristicName="Nitrate;Phosphorus",
            )

    def test_empty_dataframe_handled(self, site_params):
        empty_df = pd.DataFrame()
        with patch.object(ingest_wqp.wqp, "what_sites") as mock_what_sites:
            mock_what_sites.return_value = (empty_df, {})
            df, meta = ingest_wqp_site_data(site_params)
            assert len(df) == 0
            assert meta["row_count"] == 0

    def test_upstream_exception_propagates(self, site_params):
        with patch.object(ingest_wqp.wqp, "what_sites") as mock_what_sites:
            mock_what_sites.side_effect = RuntimeError("WQP unavailable")
            with pytest.raises(RuntimeError, match="WQP unavailable"):
                ingest_wqp_site_data(site_params)


class TestIngestWqpSiteResults:
    def test_calls_wqp_with_correct_kwargs(self, results_params, fake_results_df):
        with patch.object(ingest_wqp.wqp, "get_results") as mock_get_results:
            mock_get_results.return_value = (fake_results_df, {})
            df, meta = ingest_wqp_site_results(results_params)
            mock_get_results.assert_called_once_with(
                siteid="USGS-12345678",
                startDateLo="01-01-2020",
                startDateHi="12-31-2020",
            )
            pd.testing.assert_frame_equal(df, fake_results_df)
            assert meta["row_count"] == 2

    def test_minimal_call_only_passes_siteid(self, fake_results_df):
        params = WQPResultsParams(site_id="USGS-12345678")
        with patch.object(ingest_wqp.wqp, "get_results") as mock_get_results:
            mock_get_results.return_value = (fake_results_df, {})
            ingest_wqp_site_results(params)
            mock_get_results.assert_called_once_with(siteid="USGS-12345678")
