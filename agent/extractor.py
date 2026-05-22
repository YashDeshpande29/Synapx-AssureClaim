"""
extractor.py
------------
Extracts structured FNOL fields from raw text using:
  - Regex patterns for known structured layouts (primary)
  - Ollama local LLM (optional, set USE_OLLAMA=true)
  - OpenAI LLM fallback for unstructured/free-form text (optional, set USE_LLM=true)
"""

from __future__ import annotations

import os
import re
import json
from typing import Any

import pdfplumber


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOT_PROVIDED = re.compile(r"^\(?(not provided|n/a|none|unknown|-)\)?$", re.I)


def _clean(value: str | None) -> str | None:
    """Return None if the value is a placeholder, otherwise strip whitespace."""
    if value is None:
        return None
    v = value.strip()
    if _NOT_PROVIDED.match(v):
        return None
    return v or None


def _money(value: str | None) -> float | None:
    """Parse a dollar amount string to float."""
    if value is None:
        return None
    digits = re.sub(r"[^\d.]", "", value)
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Text loading
# ---------------------------------------------------------------------------

def load_text(file_path: str) -> str:
    """Load raw text from a .txt or .pdf file."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        pages: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n".join(pages)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()


# ---------------------------------------------------------------------------
# Regex-based extractor
# ---------------------------------------------------------------------------

# Each pattern maps a field name to a regex that captures its value in group 1.
_PATTERNS: dict[str, str] = {
    "policyNumber":       r"Policy\s+Number[:\s]+([A-Z0-9\-]+)",
    "policyholderName":   r"Policyholder\s+Name[:\s]+(.+)",
    "effectiveDateStart": r"Effective\s+Date\s+Start[:\s]+(\d{4}-\d{2}-\d{2})",
    "effectiveDateEnd":   r"Effective\s+Date\s+End[:\s]+(\d{4}-\d{2}-\d{2})",
    "dateOfLoss":         r"Date\s+of\s+Loss[:\s]+(\d{4}-\d{2}-\d{2})",
    "timeOfLoss":         r"Time\s+of\s+Loss[:\s]+(.+)",
    "location":           r"Location[:\s]+(.+)",
    "description":        r"Description[:\s]+([\s\S]+?)(?=\n===)",
    "claimantName":       r"Claimant\s+Name[:\s]+(.+)",
    "claimantPhone":      r"Claimant\s+Phone[:\s]+(.+)",
    "claimantEmail":      r"Claimant\s+Email[:\s]+(.+)",
    "thirdPartyName":     r"Third\s+Party\s+Name[:\s]+(.+)",
    "thirdPartyPhone":    r"Third\s+Party\s+Phone[:\s]+(.+)",
    "thirdPartyInsurance":r"Third\s+Party\s+Insurance[:\s]+(.+)",
    "assetType":          r"Asset\s+Type[:\s]+(.+)",
    "assetId":            r"Asset\s+ID\s*\([^)]*\)[:\s]+(.+)",
    "assetDescription":   r"Year/Make/Model[:\s]+(.+)",
    "claimType":          r"Claim\s+Type[:\s]+(.+)",
    "policeReportFiled":  r"Police\s+Report\s+Filed[:\s]+(.+)",
    "reportNumber":       r"Report\s+Number[:\s]+(.+)",
    "attachments":        r"Attachments[:\s]+(.+)",
    "initialEstimate":    r"Initial\s+Estimate[:\s]+(.+)",
    "estimatedDamage":    r"Estimated\s+Damage[:\s]+(.+)",
}


def _extract_regex(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}

    for field, pattern in _PATTERNS.items():
        m = re.search(pattern, text, re.IGNORECASE)
        raw = m.group(1).strip() if m else None
        cleaned = _clean(raw)

        if field in ("estimatedDamage", "initialEstimate"):
            fields[field] = _money(cleaned)
        elif field == "attachments":
            if cleaned:
                fields[field] = [a.strip() for a in re.split(r",\s*", cleaned) if _clean(a)]
            else:
                fields[field] = []
        else:
            fields[field] = cleaned

    # Deduplicate estimate: prefer estimatedDamage, fall back to initialEstimate
    if fields.get("estimatedDamage") is None and fields.get("initialEstimate") is not None:
        fields["estimatedDamage"] = fields["initialEstimate"]

    return fields


# ---------------------------------------------------------------------------
# LLM-based extractor (optional)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an insurance claims data extraction assistant.
Given raw FNOL (First Notice of Loss) document text, extract the following fields and return ONLY a valid JSON object.
Use null for any field not found or marked as "not provided".

Fields to extract:
- policyNumber (string)
- policyholderName (string)
- effectiveDateStart (YYYY-MM-DD string)
- effectiveDateEnd (YYYY-MM-DD string)
- dateOfLoss (YYYY-MM-DD string)
- timeOfLoss (string, e.g. "08:32 AM")
- location (string)
- description (string, full accident description)
- claimantName (string)
- claimantPhone (string)
- claimantEmail (string)
- thirdPartyName (string or null)
- thirdPartyPhone (string or null)
- thirdPartyInsurance (string or null)
- assetType (string)
- assetId (string, VIN or similar)
- assetDescription (string, year/make/model)
- estimatedDamage (number or null)
- claimType (string)
- policeReportFiled (string, "Yes" or "No")
- reportNumber (string or null)
- attachments (array of strings)
- initialEstimate (number or null)

Return ONLY a JSON object, no markdown fencing.
"""


def _extract_ollama(text: str) -> dict[str, Any]:
    """
    Extract fields using a locally running Ollama model via its
    OpenAI-compatible /v1 endpoint (no API key required).

    Configure via .env:
        USE_OLLAMA=true
        OLLAMA_BASE_URL=http://localhost:11434/v1   # default
        OLLAMA_MODEL=llama3                         # any pulled model
    """
    from openai import OpenAI  # deferred import

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    model = os.getenv("OLLAMA_MODEL", "llama3")

    client = OpenAI(
        base_url=base_url,
        api_key="ollama",  # Ollama ignores the key value but the field is required
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"FNOL Document:\n\n{text}"},
        ],
        temperature=0,
        max_tokens=1200,
    )
    raw = response.choices[0].message.content or "{}"
    # Strip markdown fences that some models add despite instructions
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"```\s*$", "", raw.strip())
    return json.loads(raw)


def _extract_openai(text: str) -> dict[str, Any]:
    from openai import OpenAI  # deferred import so regex mode has no dependency

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"FNOL Document:\n\n{text}"},
        ],
        temperature=0,
        max_tokens=1200,
    )
    raw_json = response.choices[0].message.content or "{}"
    return json.loads(raw_json)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_fields(text: str) -> dict[str, Any]:
    """
    Extract FNOL fields from raw text.

    Mode selection (checked in priority order):
      1. USE_OLLAMA=true  → local Ollama model (no API key needed)
      2. USE_LLM=true     → OpenAI (requires OPENAI_API_KEY)
      3. default          → fast regex extraction
    """
    # --- Ollama mode ---
    use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"
    if use_ollama:
        try:
            return _extract_ollama(text)
        except Exception as exc:
            print(f"[extractor] Ollama extraction failed ({exc}), falling back to regex.")

    # --- OpenAI mode ---
    use_llm = os.getenv("USE_LLM", "false").lower() == "true"
    api_key = os.getenv("OPENAI_API_KEY", "")
    if use_llm and api_key and not api_key.startswith("sk-your"):
        try:
            return _extract_openai(text)
        except Exception as exc:
            print(f"[extractor] OpenAI extraction failed ({exc}), falling back to regex.")

    # --- Regex mode (default) ---
    return _extract_regex(text)
