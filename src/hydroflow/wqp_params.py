"""Pydantic models for WQP query parameters.

These models are the validation boundary between user input and the
``dataretrieval.wqp`` calls. They:

- Validate inputs at construction time (no separate validate_*() functions).
- Resolve state names to WQP statecodes via ``ingest_utils``.
- Produce kwargs in the exact shape ``dataretrieval`` / the WQP REST API
  expects via ``to_wqp_kwargs()``.
- Produce a filesystem-safe ``slug()`` for consistent path generation.

WQP web service reference:
  https://www.waterqualitydata.us/webservices_documentation/

Design notes
------------
* ``Station/search`` (what powers ``wqp.what_sites``) does NOT filter by
  date, so date fields live only on ``WQPResultsParams``. (no wonder that failed to work at first...)
* ``characteristicName`` and ``characteristicType`` should not be combined
  (per WQP docs) — enforced by a model-level validator.
* ``siteType`` and characteristic names are case-sensitive at the WQP API;
  we preserve the user's casing and let the API reject invalid values.
* Multi-value fields are joined with ``;`` at the boundary, per the WQP
  URL-encoding convention.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hydroflow.ingest_utils import get_wqp_code


# WQP providers per the web services guide. STORET is the EPA/WQX provider.
WQPProvider = Literal["NWIS", "STORET"]


def _to_list(value: Union[str, list[str], None]) -> Optional[list[str]]:
    """Normalize str-or-list-of-str to list-of-str, preserving case."""
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    return list(value)


def _slug_part(value: str) -> str:
    """Filesystem-safe lowercase token."""
    return value.lower().replace(" ", "_")


class _WQPParamsBase(BaseModel):
    """Shared config + helpers for WQP param models."""

    model_config = ConfigDict(
        frozen=True,           # Immutable once constructed.
        str_strip_whitespace=True,
        extra="forbid",        # Typos in field names should fail LOUDLY.
    )


class WQPSiteQueryParams(_WQPParamsBase):
    """Params for ``wqp.what_sites`` (Station/search endpoint).

    Note
    ----
    The Station/search endpoint does NOT filter by date. If you need
    date-bounded queries, use ``WQPResultsParams`` against the Result
    endpoint.
    
    The sites returned by Station/search are the same as those returned by Result, but
    contain only data about the site itself (location, site type, etc.) and not the results
    which you'll get from the Result endpoint. Reading comprehension is hard. 
    """

    state_name: str = Field(..., min_length=1, description="Full US state or territory name.")
    site_type: Union[str, list[str]] = Field(
        default="Stream",
        description="Case-sensitive WQP site type(s). E.g., 'Stream', 'Lake, Reservoir, Impoundment'.",
    )
    characteristic_name: Optional[Union[str, list[str]]] = Field(
        default=None,
        description="Case-sensitive characteristic name(s). Mutually exclusive with characteristic_type.",
    )
    characteristic_type: Optional[Union[str, list[str]]] = Field(
        default=None,
        description="Case-sensitive characteristic type/group(s). Mutually exclusive with characteristic_name.",
    )
    providers: Optional[list[WQPProvider]] = Field(
        default=None,
        description="Restrict to a subset of providers. Defaults to all.",
    )

    @field_validator("state_name")
    @classmethod
    def state_must_be_known(cls, v: str) -> str:
        if get_wqp_code(v) is None:
            raise ValueError(
                f"Unknown state or territory: {v!r}. "
                f"Must match a state_name in US_STATE_FIPS_TABLE."
            )
        return v

    @field_validator("site_type", "characteristic_name", "characteristic_type")
    @classmethod
    def reject_empty_strings_in_list(cls, v):
        """An empty string in a multi-value field is almost certainly a bug."""
        if v is None:
            return v
        items = [v] if isinstance(v, str) else list(v)
        for item in items:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("Values must be non-empty strings.")
        return v

    @model_validator(mode="after")
    def no_char_name_and_type_together(self) -> "WQPSiteQueryParams":
        """WQP docs warn against combining these — results are unpredictable."""
        if self.characteristic_name and self.characteristic_type:
            raise ValueError(
                "characteristic_name and characteristic_type should not be combined. "
                "Per WQP docs, combining them produces unexpected results."
            )
        return self

    @property
    def wqp_statecode(self) -> str:
        """WQP statecode for this state, e.g. 'US:53'. Always non-None."""
        # Safe: the validator guarantees get_wqp_code() returned non-None.
        code = get_wqp_code(self.state_name)
        assert code is not None  # for type-checkers
        return code

    def to_wqp_kwargs(self) -> dict:
        """Convert to kwargs for ``dataretrieval.wqp.what_sites``.

        Multi-value fields are joined with ';' per the WQP URL convention.
        Only set keys are included so we don't override dataretrieval defaults.
        """
        kwargs: dict = {"statecode": self.wqp_statecode}

        site_types = _to_list(self.site_type)
        if site_types:
            kwargs["siteType"] = ";".join(site_types)

        char_names = _to_list(self.characteristic_name)
        if char_names:
            kwargs["characteristicName"] = ";".join(char_names)

        char_types = _to_list(self.characteristic_type)
        if char_types:
            kwargs["characteristicType"] = ";".join(char_types)

        if self.providers:
            kwargs["providers"] = ";".join(self.providers)

        return kwargs

    def slug(self) -> str:
        """Filename-safe slug, e.g. 'washington_stream'.

        If multiple site_types are given, they're joined with a hyphen.
        """
        site_types = _to_list(self.site_type) or []
        site_part = "-".join(_slug_part(s) for s in site_types) if site_types else "all"
        return f"{_slug_part(self.state_name)}_{site_part}"


class WQPResultsParams(_WQPParamsBase):
    """Params for ``wqp.get_results`` (Result/search endpoint).

    Dates are stored as ``date`` objects and formatted as MM-DD-YYYY
    at the API boundary, per the WQP web services spec.
    """

    site_id: Union[str, list[str]] = Field(
        ...,
        description="WQP site ID(s), e.g. 'USGS-12345678'. Single or list.",
    )
    characteristic_name: Optional[Union[str, list[str]]] = None
    characteristic_type: Optional[Union[str, list[str]]] = None
    start_date: Optional[date] = Field(
        default=None,
        description="Earliest data-collection activity date. Maps to startDateLo.",
    )
    end_date: Optional[date] = Field(
        default=None,
        description="Latest data-collection activity date. Maps to startDateHi.",
    )
    providers: Optional[list[WQPProvider]] = None

    @field_validator("site_id", "characteristic_name", "characteristic_type")
    @classmethod
    def reject_empty_strings_in_list(cls, v):
        if v is None:
            return v
        items = [v] if isinstance(v, str) else list(v)
        if not items:
            raise ValueError("Must provide at least one value.")
        for item in items:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("Values must be non-empty strings.")
        return v

    @model_validator(mode="after")
    def end_after_start(self) -> "WQPResultsParams":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self

    @model_validator(mode="after")
    def no_char_name_and_type_together(self) -> "WQPResultsParams":
        if self.characteristic_name and self.characteristic_type:
            raise ValueError(
                "characteristic_name and characteristic_type should not be combined. "
                "Per WQP docs, combining them produces unexpected results."
            )
        return self

    def to_wqp_kwargs(self) -> dict:
        """Convert to kwargs for ``dataretrieval.wqp.get_results``."""
        site_ids = _to_list(self.site_id) or []
        kwargs: dict = {"siteid": ";".join(site_ids)}

        char_names = _to_list(self.characteristic_name)
        if char_names:
            kwargs["characteristicName"] = ";".join(char_names)

        char_types = _to_list(self.characteristic_type)
        if char_types:
            kwargs["characteristicType"] = ";".join(char_types)

        if self.start_date:
            kwargs["startDateLo"] = self.start_date.strftime("%m-%d-%Y")
        if self.end_date:
            kwargs["startDateHi"] = self.end_date.strftime("%m-%d-%Y")

        if self.providers:
            kwargs["providers"] = ";".join(self.providers)

        return kwargs
