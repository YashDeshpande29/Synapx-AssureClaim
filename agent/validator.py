"""
Checks extracted FNOL fields for:
  1. Missing mandatory fields
  2. Basic consistency issues (e.g. loss date outside policy effective period)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


MANDATORY_FIELDS: list[str] = [
    "policyNumber",
    "policyholderName",
    "effectiveDateStart",
    "effectiveDateEnd",
    "dateOfLoss",
    "timeOfLoss",
    "location",
    "description",
    "claimantName",
    "claimantPhone",
    "assetType",
    "assetId",
    "estimatedDamage",
    "claimType",
    "initialEstimate",
]


def find_missing_fields(fields: dict[str, Any]) -> list[str]:
    """Return a list of mandatory field names that are None/empty."""
    missing: list[str] = []
    for field in MANDATORY_FIELDS:
        value = fields.get(field)
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
        elif isinstance(value, list) and len(value) == 0:
            pass  # attachments being empty is allowed
    return missing


def find_inconsistencies(fields: dict[str, Any]) -> list[str]:

    issues: list[str] = []

    # Check loss date is within effective period
    try:
        date_loss = datetime.strptime(fields["dateOfLoss"], "%Y-%m-%d")
        date_start = datetime.strptime(fields["effectiveDateStart"], "%Y-%m-%d")
        date_end = datetime.strptime(fields["effectiveDateEnd"], "%Y-%m-%d")

        if date_loss < date_start:
            issues.append(
                f"Date of loss ({fields['dateOfLoss']}) is before policy effective start "
                f"({fields['effectiveDateStart']})."
            )
        if date_loss > date_end:
            issues.append(
                f"Date of loss ({fields['dateOfLoss']}) is after policy effective end "
                f"({fields['effectiveDateEnd']})."
            )
    except (KeyError, TypeError, ValueError):
        pass  
    
    initial = fields.get("initialEstimate")
    estimated = fields.get("estimatedDamage")
    if initial and estimated:
        delta_pct = abs(initial - estimated) / max(initial, estimated)
        if delta_pct > 0.05:
            issues.append(
                f"Initial estimate (${initial:,.0f}) differs significantly from "
                f"estimated damage (${estimated:,.0f})."
            )

    return issues
