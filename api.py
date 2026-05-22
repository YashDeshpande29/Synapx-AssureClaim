"""
api.py
------
FastAPI REST service for the AssureClaim FNOL processing agent.

Endpoints:
  POST /process       — process a file by path (server-local)
  POST /process-text  — process raw FNOL text
  POST /upload        — upload a file directly
  GET  /health        — liveness check
"""

from __future__ import annotations

import io
import tempfile
import os

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.pipeline import process_file, process_text

app = FastAPI(
    title="AssureClaim — Autonomous Insurance Claims Processing Agent",
    description=(
        "Extracts fields from FNOL documents, identifies missing/inconsistent data, "
        "classifies claims, and routes them to the correct workflow."
    ),
    version="1.0.0",
)

_raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost,http://localhost:80,http://localhost:5173,http://127.0.0.1:5173",
)
_allow_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FilePathRequest(BaseModel):
    file_path: str


class RawTextRequest(BaseModel):
    text: str


class ClaimResult(BaseModel):
    extractedFields: dict
    missingFields: list[str]
    recommendedRoute: str
    reasoning: str



@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "AssureClaim"}


@app.post("/process", response_model=ClaimResult, summary="Process FNOL file by server path")
def process_by_path(request: FilePathRequest) -> ClaimResult:
    """
    Process an FNOL file located on the server.
    Accepts .txt or .pdf files.
    """
    if not os.path.isfile(request.file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
    try:
        result = process_file(request.file_path)
        return ClaimResult(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/process-text", response_model=ClaimResult, summary="Process raw FNOL text")
def process_raw_text(request: RawTextRequest) -> ClaimResult:
    """
    Process raw FNOL text submitted directly in the request body.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="'text' field must not be empty.")
    try:
        result = process_text(request.text)
        return ClaimResult(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/upload", response_model=ClaimResult, summary="Upload and process an FNOL file")
async def upload_and_process(file: UploadFile = File(...)) -> ClaimResult:
    """
    Upload an FNOL document (.txt or .pdf) and receive the processing result.
    """
    allowed_extensions = {".txt", ".pdf"}
    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {allowed_extensions}",
        )

    content = await file.read()

    # Write to a secure temporary file
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=ext.lower(), mode="wb"
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = process_file(tmp_path)
        return ClaimResult(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        os.unlink(tmp_path)
