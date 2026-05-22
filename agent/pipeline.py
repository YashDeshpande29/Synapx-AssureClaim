"""
Orchestrates the full FNOL processing pipeline:
  load text → extract fields → validate → route → return JSON result
"""

from __future__ import annotations

import json
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from agent.extractor import extract_fields, load_text
from agent.validator import find_missing_fields, find_inconsistencies
from agent.router import route_claim


def process_text(text: str) -> dict[str, Any]:
    """
    Run the full agent pipeline on raw FNOL text.

    Returns the standard output dict:
    {
        "extractedFields": {...},
        "missingFields": [...],
        "recommendedRoute": "...",
        "reasoning": "..."
    }
    """
    fields = extract_fields(text)
    missing = find_missing_fields(fields)
    inconsistencies = find_inconsistencies(fields)
    route, reasoning = route_claim(fields, missing, inconsistencies)

    return {
        "extractedFields": fields,
        "missingFields": missing,
        "recommendedRoute": route,
        "reasoning": reasoning,
    }


def process_file(file_path: str) -> dict[str, Any]:
    text = load_text(file_path)
    return process_text(text)


def process_file_pretty(file_path: str) -> str:
    
    result = process_file(file_path)
    return json.dumps(result, indent=2)
