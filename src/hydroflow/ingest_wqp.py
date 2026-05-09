from src.hydroflow.ingest_utils import get_wqp_statecode_from_state
from dataretrieval import wqp
from datetime import datetime, timezone
import pandas as pd
from typing import Tuple    

# --- State FIPS and WQP Code Mappings are in ingest_utils.py---

### Helper functions for ingesting WQP data and saving to raw and bronze landing zones.

def get_bronze_path(state_name: str, site_type: str) -> str:
    """Generate the path for the bronze landing file based on the state name and site type.
    Currently hard-coded to save in a single file per state and site type, but we could easily
    modify this to include more parameters (e.g., characteristics, date range, etc.) if we wanted
    to save more granular files in the future."""
    return f"data/bronze/{state_name.lower().replace(' ', '_')}_{site_type.lower().replace(' ', '_')}_sites.parquet"


def get_raw_path(state_name: str, site_type: str) -> str:
    """Generate the path for the raw landing file based on the state name and site type."""
    return f"data/raw/{state_name.lower().replace(' ', '_')}_{site_type.lower().replace(' ', '_')}_sites.csv"


def save_data_to_raw(df: pd.DataFrame, state_name: str, site_type: str) -> str:
    """ Save the raw DataFrame to the raw landing zone as a CSV file. Returns the path to the saved file for query purposes. Currently hard-coded to save in a single file per state and site type, but we could easily modify this to include more parameters (e.g., characteristics, date range, etc.) if we wanted to save more granular files in the future."""

    raw_path = get_raw_path(state_name, site_type)
    df.to_csv(raw_path, index=False)
    print(f"Saved raw landing file to: {raw_path}")
    return raw_path


def save_data_to_bronze(df: pd.DataFrame, state_name: str, site_type: str) -> str:
    """ Save the raw DataFrame to the bronze zone as a parquet file. Returns the path to the saved file for query purposes. Currently hard-coded to save in a single file per state and site type, but we could easily modify this to include more parameters (e.g., characteristics, date range, etc.) if we wanted to save more granular files in the future."""
    
    bronze_path = get_bronze_path(state_name, site_type)
    df.to_parquet(bronze_path, index=False)
    print(f"Saved bronze landing file to: {bronze_path}")
    return bronze_path

def ingest_wqp_site_data_by_state(state_name: str, site_type: str = 'Stream', characteristics: list = None, start_date: str = None, end_date: str = None) -> tuple[pd.DataFrame, dict]:
    """Ingest WQP data for a specific state and site type, and for specific characteristics and date range. Returns a tuple of the raw DataFrame and the query metadata."""

    # validate inputs
    if not state_name:
        raise ValueError("State name is required.")
    if not site_type:
        raise ValueError("Site type is required.")
    if characteristics and not isinstance(characteristics, list):
        raise ValueError("Characteristics must be a list of strings.")
    if start_date and not isinstance(start_date, str):
        raise ValueError("Start date must be a string in 'YYYY-MM-DD' format.")
    if end_date and not isinstance(end_date, str):
        raise ValueError("End date must be a string in 'YYYY-MM-DD' format.")

    # the dataretrieval package uses the WQP query code (e.g., 'US:53' for Washington) to query the WQP API, so we need to convert our state name to the WQP code using our utility function.
    fips_code = get_wqp_statecode_from_state(state_name)

    print(f"Fetching {site_type} monitoring sites in {state_name}...")

    # Step 1: Find the given site types in the given state
    sites_df_raw, metadata = wqp.what_sites(statecode=fips_code, siteType=site_type)
    print(f"Found {len(sites_df_raw)} {site_type} monitoring sites in state:{fips_code}, type:{site_type} for the period {start_date} to {end_date}.")

    return sites_df_raw, metadata

def ingest_wqp_site_results(site_id: str) -> tuple[pd.DataFrame, dict]:
    """Ingest WQP results data for a specific site. This is ALL dates, ALL characteristics. Returns a tuple of the raw DataFrame and the query metadata."""

    # validate inputs
    if not site_id:
        raise ValueError("Site ID is required.")

    return wqp.get_results(
        siteid=site_id
    )