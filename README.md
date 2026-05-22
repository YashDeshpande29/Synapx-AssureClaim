# AssureClaim - Autonomous Insurance Claims Processing Agent

> Autonomous FNOL processing pipeline with React UI, FastAPI backend, and Docker deployment.

---

## Quick Start (Docker - recommended)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

```bash
git clone <repo-url>
cd Synapx
docker compose up --build
```

| Service      | URL                        |
|--------------|----------------------------|
| React UI     | http://localhost           |
| REST API     | http://localhost:8000      |
| Swagger docs | http://localhost:8000/docs |

That is it. No Python or Node installation required. The `.env` file is included and pre-configured for out-of-the-box regex mode (no API keys required).

---

## What It Does

AssureClaim is a lightweight agent that processes **FNOL (First Notice of Loss)** insurance documents end-to-end:

1. **Extracts** 22 structured fields from PDF or TXT documents
2. **Validates** mandatory fields and checks consistency (e.g. loss date vs. policy period)
3. **Routes** the claim to the correct workflow using priority-ordered business rules
4. **Explains** the routing decision in plain English

---

## Architecture

```
Browser  -->  React UI (nginx :80)  -->  FastAPI Backend (:8000)
                                               |
                                     Agent Pipeline
                                     extractor -> validator -> router
```

### Project Structure

```
Synapx/
|-- agent/
|   |-- extractor.py       # Field extraction (regex + Ollama/OpenAI fallback)
|   |-- validator.py       # Missing-field and consistency checks
|   |-- router.py          # Priority-ordered routing rules engine
|   +-- pipeline.py        # Orchestrator
|-- frontend/
|   |-- src/
|   |   |-- App.jsx        # Main React component
|   |   +-- App.module.css # Scoped styles
|   |-- Dockerfile         # Multi-stage: Node build -> nginx serve
|   |-- nginx.conf         # SPA routing config
|   +-- package.json
|-- sample_fnols/          # 5 dummy FNOL documents (.txt)
|-- api.py                 # FastAPI service
|-- cli.py                 # Command-line interface
|-- Dockerfile             # Backend container
|-- docker-compose.yml     # One-command deployment
|-- .env                   # Environment config (included for easy setup)
+-- requirements.txt
```

---

## Routing Rules

Rules are evaluated in **priority order** - first match wins.

| Priority | Condition                                               | Route                |
|----------|---------------------------------------------------------|----------------------|
| 1        | Description contains `fraud`, `inconsistent`, `staged` | Investigation Flag   |
| 2        | Any mandatory field is missing                          | Manual Review        |
| 3        | Claim type = Injury                                     | Specialist Queue     |
| 4        | Estimated damage < $25,000                              | Fast-track           |
| 5        | Fallback                                                | Standard Review      |

---

## Output Format

```json
{
  "extractedFields": {
    "policyNumber": "POL-2024-00123",
    "policyholderName": "James Robert Harrington",
    "dateOfLoss": "2024-11-15",
    "estimatedDamage": 8500.0,
    "claimType": "Property Damage"
  },
  "missingFields": [],
  "recommendedRoute": "Fast-track",
  "reasoning": "All mandatory fields are present. Estimated damage ($8,500.00) is below the $25,000 fast-track threshold. No fraud indicators detected."
}
```

---

## Sample FNOL Test Cases

| File         | Scenario                                          | Expected Route     |
|--------------|---------------------------------------------------|--------------------|
| fnol_001.txt | Rear-end collision, $8,500 damage                 | Fast-track         |
| fnol_002.txt | Hit-and-run, description says "inconsistent"      | Investigation Flag |
| fnol_003.txt | Injury claim - whiplash + fractured wrist         | Specialist Queue   |
| fnol_004.txt | Incomplete form, expired policy                   | Manual Review      |
| fnol_005.txt | Theft claim - "staged", "fraud", "inconsistent"   | Investigation Flag |

---

## Extraction Modes

| Mode                  | How to enable                            | Requires               |
|-----------------------|------------------------------------------|------------------------|
| **Regex** (default)   | nothing                                  | nothing - works out of the box |
| **Ollama** (local LLM)| `USE_OLLAMA=true` in `.env`              | Ollama running locally |
| **OpenAI** (cloud LLM)| `USE_LLM=true` + `OPENAI_API_KEY` in `.env` | OpenAI API key      |

Priority: Ollama -> OpenAI -> Regex. Falls back automatically on failure.

### Using Ollama (optional)

```bash
ollama pull llama3
# Edit .env:
#   USE_OLLAMA=true
#   OLLAMA_MODEL=llama3
docker compose up --build
```

`OLLAMA_BASE_URL` defaults to `http://host.docker.internal:11434/v1` so the container can reach Ollama on your host machine.

---

## Local Development (without Docker)

```bash
# Backend
pip install -r requirements.txt
uvicorn api:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

### CLI

```bash
python cli.py sample_fnols/fnol_001.txt          # pretty print
python cli.py sample_fnols/fnol_001.txt --json   # raw JSON
python cli.py --all                               # all 5 samples
```

---

## Environment Variables (.env)

| Variable          | Default                                    | Description                  |
|-------------------|--------------------------------------------|------------------------------|
| `USE_OLLAMA`      | `false`                                    | Enable local Ollama LLM extraction |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434/v1`     | Ollama API endpoint          |
| `OLLAMA_MODEL`    | `llama3`                                   | Model name to use            |
| `USE_LLM`         | `false`                                    | Enable OpenAI extraction     |
| `OPENAI_API_KEY`  | -                                          | OpenAI API key               |

---

## Tech Stack

| Layer            | Technology                | Purpose                                       |
|------------------|---------------------------|-----------------------------------------------|
| Frontend         | React 18 + Vite           | Interactive UI                                |
| Serving          | nginx                     | Serves React build, proxies `/api` to backend |
| Backend          | FastAPI + uvicorn         | REST API                                      |
| Extraction       | Regex / Ollama / OpenAI   | FNOL field parsing                            |
| PDF parsing      | pdfplumber                | Read PDF documents                            |
| Containerisation | Docker + Docker Compose   | One-command deployment                        |
