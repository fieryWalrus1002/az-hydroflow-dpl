"""Ingest WQP site and result data into the raw and bronze landing zones.

The decomposition here puts the network call (``dataretrieval.wqp``) at
the very edge, with everything else as pure, testable functions that
operate on ``WQPSiteQueryParams`` / ``WQPResultsParams``.

This keeps the data retrieval logic separate from the data transformation and persistence
and makes it easier to test the transformation and persistence logic without needing to
mock the network calls.
"""

from datetime import datetime, timezone
from typing import Tuple
from pathlib import Path

from dataretrieval import wqp
import pandas as pd

from hydroflow.wqp_params import WQPResultsParams, WQPSiteQueryParams


# Path helpers to break the evil hard-coded string spells
def get_raw_path(params: WQPSiteQueryParams, base_dir: str = "data/raw") -> str:
    """Path for the raw CSV landing file for a site query."""
    return f"{base_dir}/{params.slug()}_sites.csv"


def get_bronze_path(params: WQPSiteQueryParams, base_dir: str = "data/bronze") -> str:
    """Path for the bronze Parquet file for a site query."""
    return f"{base_dir}/{params.slug()}_sites.parquet"


# Now the persistence functions here


def save_data_to_raw(
    df: pd.DataFrame, params: WQPSiteQueryParams, base_dir: str = "data/raw"
) -> str:
    """Save a DataFrame to the raw landing zone as CSV. Returns the path."""
    raw_path = get_raw_path(params, base_dir=base_dir)
    Path(raw_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(raw_path, index=False)
    print(f"Saved raw landing file to: {raw_path}")
    return raw_path


def save_data_to_bronze(
    df: pd.DataFrame, params: WQPSiteQueryParams, base_dir: str = "data/bronze"
) -> str:
    """Save a DataFrame to the bronze zone as Parquet. Returns the path."""
    bronze_path = get_bronze_path(params, base_dir=base_dir)
    Path(bronze_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(bronze_path, index=False)
    print(f"Saved bronze landing file to: {bronze_path}")
    return bronze_path


# Now the metadata envelope builder, which is a pure function
# that lets us get rid of the boilerplate validation we had before.
# Have a single source of truth for what metadata we want to capture for lineage.


def build_query_metadata(
    params: WQPSiteQueryParams | WQPResultsParams,
    row_count: int,
    source_metadata: object = None,
) -> dict:
    """Build a consistent metadata envelope around a query result.

    This is what downstream bronze/silver consumers can rely on for lineage,
    regardless of what ``dataretrieval`` returns in its own metadata object.
    """
    return {
        "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
        "query_params": params.model_dump(mode="json"),
        "wqp_kwargs": params.to_wqp_kwargs(),
        "row_count": row_count,
        "source_metadata": source_metadata,
    }


# ----- The Orchestrators, the only functions that touch the network, and they just call the pure functions above.


def ingest_wqp_site_data(params: WQPSiteQueryParams) -> Tuple[pd.DataFrame, dict]:
    """Fetch monitoring sites from WQP for the given query params.

    Returns a tuple of (DataFrame, metadata envelope).
    """
    kwargs = params.to_wqp_kwargs()
    print(f"Fetching WQP sites with kwargs: {kwargs}")

    sites_df, source_metadata = wqp.what_sites(**kwargs)

    print(
        f"Found {len(sites_df)} sites for "
        f"statecode={params.wqp_statecode}, site_type={params.site_type}."
    )

    metadata = build_query_metadata(
        params, row_count=len(sites_df), source_metadata=source_metadata
    )
    return sites_df, metadata


def ingest_wqp_site_results(params: WQPResultsParams) -> Tuple[pd.DataFrame, dict]:
    """Fetch WQP results for the given query params.

    Returns a tuple of (DataFrame, metadata envelope).
    """
    kwargs = params.to_wqp_kwargs()
    print(f"Fetching WQP results with kwargs: {kwargs}")

    results_df, source_metadata = wqp.get_results(**kwargs)

    print(f"Fetched {len(results_df)} result rows.")

    metadata = build_query_metadata(
        params, row_count=len(results_df), source_metadata=source_metadata
    )
    return results_df, metadata
