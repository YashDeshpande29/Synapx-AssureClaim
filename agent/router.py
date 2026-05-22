"""
Applies business routing rules to a validated FNOL claim.

Priority order (highest → lowest):
  1. Investigation Flag  — fraud keywords in description
  2. Manual Review       — any mandatory field is missing
  3. Specialist Queue    — claim type is Injury
  4. Fast-track          — damage < $25,000 and all fields present
  5. Standard Review     — fallback (damage >= $25,000, no flags)
"""

from __future__ import annotations

import re
from typing import Any


FAST_TRACK_THRESHOLD = 25_000.0

FRAUD_KEYWORDS: list[str] = [
    "fraud",
    "fraudulent",
    "inconsistent",
    "staged",
    "false claim",
    "fabricated",
    "suspicious",
]

INJURY_CLAIM_TYPES: list[str] = [
    "injury",
    "bodily injury",
    "personal injury",
    "medical",
]


def _contains_fraud_keywords(text: str | None) -> list[str]:
    if not text:
        return []
    text_lower = text.lower()
    return [kw for kw in FRAUD_KEYWORDS if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)]


def _is_injury_claim(claim_type: str | None) -> bool:
    if not claim_type:
        return False
    claim_lower = claim_type.lower()
    return any(t in claim_lower for t in INJURY_CLAIM_TYPES)


def route_claim(
    fields: dict[str, Any],
    missing_fields: list[str],
    inconsistencies: list[str],
) -> tuple[str, str]:

    description: str | None = fields.get("description")
    claim_type: str | None = fields.get("claimType")
    estimated_damage: float | None = fields.get("estimatedDamage")

    reasons: list[str] = []

    # --- Rule 1: Investigation Flag ---
    matched_keywords = _contains_fraud_keywords(description)
    if matched_keywords:
        reasons.append(
            f"Description contains fraud indicator keyword(s): "
            f"{', '.join(repr(k) for k in matched_keywords)}."
        )
        reasons += [f"Consistency issue: {i}" for i in inconsistencies]
        return "Investigation Flag", " ".join(reasons)

    # --- Rule 2: Manual Review (missing fields) ---
    if missing_fields:
        reasons.append(
            f"The following mandatory field(s) are missing or not provided: "
            f"{', '.join(missing_fields)}."
        )
        reasons.append("Claim cannot be processed automatically without complete information.")
        reasons += [f"Consistency issue: {i}" for i in inconsistencies]
        return "Manual Review", " ".join(reasons)

    # --- Rule 3: Specialist Queue (Injury) ---
    if _is_injury_claim(claim_type):
        reasons.append(
            f"Claim type is '{claim_type}', which requires specialist handling."
        )
        if estimated_damage is not None:
            reasons.append(f"Estimated damage: ${estimated_damage:,.2f}.")
        reasons += [f"Consistency issue: {i}" for i in inconsistencies]
        return "Specialist Queue", " ".join(reasons)

    # --- Rule 4: Fast-track ---
    if estimated_damage is not None and estimated_damage < FAST_TRACK_THRESHOLD:
        reasons.append(
            f"All mandatory fields are present. "
            f"Estimated damage (${estimated_damage:,.2f}) is below the "
            f"${FAST_TRACK_THRESHOLD:,.0f} fast-track threshold. "
            f"No fraud indicators detected. Claim type is '{claim_type}'."
        )
        reasons += [f"Consistency issue: {i}" for i in inconsistencies]
        return "Fast-track", " ".join(reasons)

    # --- Rule 5: Standard Review (fallback) ---
    reasons.append(
        f"All mandatory fields are present but estimated damage "
        f"(${estimated_damage:,.2f}) meets or exceeds the ${FAST_TRACK_THRESHOLD:,.0f} threshold. "
        f"Routed for standard adjuster review."
    )
    reasons += [f"Consistency issue: {i}" for i in inconsistencies]
    return "Standard Review", " ".join(reasons)
