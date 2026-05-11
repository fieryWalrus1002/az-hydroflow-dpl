"""State name / FIPS code / WQP query code lookups.

Single source of truth for the mapping between US state/territory names,
their 2-digit FIPS codes (NIST FIPS PUB 5-2), and the `statecode` argument
format expected by the WQP web services (e.g. ``US:53`` for Washington).

See: https://www.waterqualitydata.us/webservices_documentation/
"""
from typing import Optional

# Defined by https://nvlpubs.nist.gov/nistpubs/Legacy/FIPS/fipspub5-2.pdf
# Single source of truth for State Names, 2-digit FIPS codes, and USGS WQP Query Codes
US_STATE_FIPS_TABLE = [
    {"state_name": "Alabama", "fips_code": "01", "wqp_code": "US:01"},
    {"state_name": "Alaska", "fips_code": "02", "wqp_code": "US:02"},
    {"state_name": "Arizona", "fips_code": "04", "wqp_code": "US:04"},
    {"state_name": "Arkansas", "fips_code": "05", "wqp_code": "US:05"},
    {"state_name": "California", "fips_code": "06", "wqp_code": "US:06"},
    {"state_name": "Colorado", "fips_code": "08", "wqp_code": "US:08"},
    {"state_name": "Connecticut", "fips_code": "09", "wqp_code": "US:09"},
    {"state_name": "Delaware", "fips_code": "10", "wqp_code": "US:10"},
    {"state_name": "District of Columbia", "fips_code": "11", "wqp_code": "US:11"},
    {"state_name": "Florida", "fips_code": "12", "wqp_code": "US:12"},
    {"state_name": "Georgia", "fips_code": "13", "wqp_code": "US:13"},
    {"state_name": "Hawaii", "fips_code": "15", "wqp_code": "US:15"},
    {"state_name": "Idaho", "fips_code": "16", "wqp_code": "US:16"},
    {"state_name": "Illinois", "fips_code": "17", "wqp_code": "US:17"},
    {"state_name": "Indiana", "fips_code": "18", "wqp_code": "US:18"},
    {"state_name": "Iowa", "fips_code": "19", "wqp_code": "US:19"},
    {"state_name": "Kansas", "fips_code": "20", "wqp_code": "US:20"},
    {"state_name": "Kentucky", "fips_code": "21", "wqp_code": "US:21"},
    {"state_name": "Louisiana", "fips_code": "22", "wqp_code": "US:22"},
    {"state_name": "Maine", "fips_code": "23", "wqp_code": "US:23"},
    {"state_name": "Maryland", "fips_code": "24", "wqp_code": "US:24"},
    {"state_name": "Massachusetts", "fips_code": "25", "wqp_code": "US:25"},
    {"state_name": "Michigan", "fips_code": "26", "wqp_code": "US:26"},
    {"state_name": "Minnesota", "fips_code": "27", "wqp_code": "US:27"},
    {"state_name": "Mississippi", "fips_code": "28", "wqp_code": "US:28"},
    {"state_name": "Missouri", "fips_code": "29", "wqp_code": "US:29"},
    {"state_name": "Montana", "fips_code": "30", "wqp_code": "US:30"},
    {"state_name": "Nebraska", "fips_code": "31", "wqp_code": "US:31"},
    {"state_name": "Nevada", "fips_code": "32", "wqp_code": "US:32"},
    {"state_name": "New Hampshire", "fips_code": "33", "wqp_code": "US:33"},
    {"state_name": "New Jersey", "fips_code": "34", "wqp_code": "US:34"},
    {"state_name": "New Mexico", "fips_code": "35", "wqp_code": "US:35"},
    {"state_name": "New York", "fips_code": "36", "wqp_code": "US:36"},
    {"state_name": "North Carolina", "fips_code": "37", "wqp_code": "US:37"},
    {"state_name": "North Dakota", "fips_code": "38", "wqp_code": "US:38"},
    {"state_name": "Ohio", "fips_code": "39", "wqp_code": "US:39"},
    {"state_name": "Oklahoma", "fips_code": "40", "wqp_code": "US:40"},
    {"state_name": "Oregon", "fips_code": "41", "wqp_code": "US:41"},
    {"state_name": "Pennsylvania", "fips_code": "42", "wqp_code": "US:42"},
    {"state_name": "Rhode Island", "fips_code": "44", "wqp_code": "US:44"},
    {"state_name": "South Carolina", "fips_code": "45", "wqp_code": "US:45"},
    {"state_name": "South Dakota", "fips_code": "46", "wqp_code": "US:46"},
    {"state_name": "Tennessee", "fips_code": "47", "wqp_code": "US:47"},
    {"state_name": "Texas", "fips_code": "48", "wqp_code": "US:48"},
    {"state_name": "Utah", "fips_code": "49", "wqp_code": "US:49"},
    {"state_name": "Vermont", "fips_code": "50", "wqp_code": "US:50"},
    {"state_name": "Virginia", "fips_code": "51", "wqp_code": "US:51"},
    {"state_name": "Washington", "fips_code": "53", "wqp_code": "US:53"},
    {"state_name": "West Virginia", "fips_code": "54", "wqp_code": "US:54"},
    {"state_name": "Wisconsin", "fips_code": "55", "wqp_code": "US:55"},
    {"state_name": "Wyoming", "fips_code": "56", "wqp_code": "US:56"},
    # Key Territories
    {"state_name": "American Samoa", "fips_code": "60", "wqp_code": "US:60"},
    {"state_name": "Guam", "fips_code": "66", "wqp_code": "US:66"},
    {"state_name": "Northern Mariana Islands", "fips_code": "69", "wqp_code": "US:69"},
    {"state_name": "Puerto Rico", "fips_code": "72", "wqp_code": "US:72"},
    {"state_name": "Virgin Islands", "fips_code": "78", "wqp_code": "US:78"}
]

# Pre-built indexes for O(1) lookups. Built once at import time.
# Previous method built them every time the function was called
#
_BY_STATE = {row["state_name"].lower(): row for row in US_STATE_FIPS_TABLE}
_BY_WQP = {row["wqp_code"].upper(): row for row in US_STATE_FIPS_TABLE}
_BY_FIPS = {row["fips_code"]: row for row in US_STATE_FIPS_TABLE}


def _normalize_state_name(state_name: str) -> str:
    """Lowercase and strip whitespace for tolerant matching."""
    return state_name.strip().lower()

def get_wqp_code(state_name: str) -> Optional[str]:
    """Retrieve the WQP query code (e.g., 'US:53') using the full state name.
    Case-insensitive and whitespace-tolerant. Returns None for unknown states.
    """
    row = _BY_STATE.get(_normalize_state_name(state_name))
    return row["wqp_code"] if row else None


def get_state_from_wqp(wqp_code: str) -> Optional[str]:
    """Retrieve the full state name using the WQP query code (e.g., 'US:53')."""
    row = _BY_WQP.get(wqp_code.strip().upper())
    return row["state_name"] if row else None


def get_fips_from_state(state_name: str) -> Optional[str]:
    """Retrieve the 2-digit FIPS code using the full state name."""
    row = _BY_STATE.get(_normalize_state_name(state_name))
    return row["fips_code"] if row else None

def get_state_from_fips(fips_code: str) -> Optional[str]:
    """Retrieve the full state name using the 2-digit FIPS code.

    Accepts ints or strings; pads to 2 digits.
    """
    fips_str = str(fips_code).zfill(2)
    row = _BY_FIPS.get(fips_str)
    return row["state_name"] if row else None