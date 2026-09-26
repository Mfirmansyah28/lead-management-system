# AI-Assisted Mini Lead Management System

A scoped backend implementation for the take-home assignment **AI-Assisted Mini Lead Management System**.

The service manages a messy CRM-style lead dataset and provides:

1. A lead store and REST API
2. AI-assisted/deterministic lead deduplication using blocking + fuzzy similarity
3. AI-assisted source extraction from free-text lead notes using a deterministic rules/regex approach
4. A basic dashboard endpoint with counts by lead status and source channel
5. Meaningful automated tests for normalization, deduplication, source extraction, ingestion, filtering, and dashboard behavior

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite
- RapidFuzz
- Pytest

No paid LLM API is required. The assignment explicitly allows a rules/regex or hybrid approach for source extraction, so this implementation uses deterministic rules to keep the solution reproducible and cost-free.

## Project structure

```text
.
├── app/
│   ├── api/
│   │   └── leads.py
│   ├── db/
│   │   ├── database.py
│   │   └── models.py
│   ├── schemas/
│   │   └── lead.py
│   ├── services/
│   │   ├── dedup.py
│   │   ├── normalization.py
│   │   └── source_extraction.py
│   └── main.py
├── data/
│   ├── leads_seed.csv
│   ├── website_form_submissions.json
│   └── leads.db
├── scripts/
│   ├── __init__.py
│   └── seed_database.py
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_dedup.py
│   ├── test_normalization.py
│   └── test_source_extraction.py
├── requirements.txt
└── README.md
```

## Design decisions

### Storage

SQLite was selected because the assignment is intentionally scoped to a small internal service and the seed dataset contains about 2,000 records. It requires no external database service or credentials and is sufficient for the requested API and analysis workflow.

The schema preserves the useful CRM fields while adding normalized fields used for matching:

- `email_normalized`
- `phone_normalized`
- `name_normalized`
- `company_normalized`
- `source_channel`
- `source_detail`

### Data normalization

The seed CSV is deliberately messy. Before storing records, the project normalizes:

- whitespace
- email casing
- phone numbers to digits
- names and company names for matching
- lead-status casing/variants
- common date formats

For example, ` New`, `new`, and `NEW` are normalized to `New`, while `closed won` variants are normalized to `Closed Won`.

The original display values are still retained where useful; normalized values are used primarily for filtering and identity matching.

## API

### `GET /leads`

List leads with optional filters:

```text
GET /leads/?status=New&owner=Alice&country=Singapore&q=acme
```

Supported filters:

- `status`
- `owner`
- `country`
- `q` — searches name, company, and email fields
- `limit`
- `offset`

### `GET /leads/{id}`

Return one lead by database ID.

### `PATCH /leads/{id}`

Update the requested lead fields:

```json
{
  "status": "Qualified",
  "owner": "Alice Tan",
  "notes": "Follow up next week"
}
```

### `GET /leads/export`

Export the current filtered view as CSV.

The same filters used by `GET /leads` are supported.

### `POST /leads/ingest`

Accept a website-form submission shaped like the provided `website_form_submissions.json` entries.

A single object or a JSON array is accepted:

```json
{
  "form_id": "form_demo_request",
  "form_name": "Book a Demo",
  "page_url": "/book-a-demo",
  "submitted_at": "2026-06-12T18:17:00Z",
  "name": "Karim Toure",
  "email": "k.toure@liutrading.biz",
  "phone": "+61 462 210 338",
  "company": "Liu Trading Studio",
  "country": "Australia",
  "message": "Following up after our earlier conversation, please send more info."
}
```

Ingestion:

1. Normalizes identifying fields
2. Looks for an existing person using exact normalized email/phone first
3. Uses blocked candidate matching by normalized name/company when exact identifiers are unavailable
4. Scores candidates using the same fuzzy identity signals used by the deduplication service
5. Updates an existing lead when confidence is high enough
6. Creates a new lead otherwise
7. Extracts the source channel/detail from the submitted message

A convenience CSV endpoint, `POST /leads/ingest-csv`, is also included, but the required assignment endpoint is the JSON-based `/leads/ingest`.

### `POST /leads/dedupe-candidates`

Returns likely duplicate pairs ranked by confidence.

Optional query parameter:

```text
min_confidence=0.72
```

Example response shape:

```json
{
  "candidate_pairs_considered": 123,
  "candidates": [
    {
      "lead_a": {"id": 1, "record_id": 1001, "name": "Jane Tan"},
      "lead_b": {"id": 2, "record_id": 1044, "name": "Jane Tann"},
      "confidence": 0.98,
      "reason": "exact normalized email match; very similar names; same country",
      "signals": [
        "exact normalized email match",
        "very similar names",
        "same country"
      ]
    }
  ]
}
```

The endpoint does **not** automatically merge records. The assignment only asks for candidate pairs with confidence/explanation.

## Deduplication approach

A full pairwise comparison across roughly 2,000 records would create around 4 million possible comparisons. The implementation therefore uses a blocking/candidate-generation stage first.

Candidate blocks are generated from normalized:

- phone
- exact email
- non-generic email domain
- company
- name
- name + country

Very large blocks are skipped to avoid creating noisy or expensive candidate sets.

Surviving pairs are scored with RapidFuzz using:

- name similarity: 35%
- company similarity: 20%
- email similarity: 20%
- phone similarity: 20%
- country agreement: 5%

Exact normalized email/phone matches receive a stronger confidence floor when another identity signal also agrees.

This approach is intentionally hybrid/deterministic rather than calling an LLM for every pair. It is fast, reproducible, explainable, and avoids unnecessary API cost while still handling spelling and formatting differences.

## Source extraction

### `POST /leads/source-extract`

Accepts raw text and returns a structured result:

```json
{
  "text": "Scanned the QR code at our Singapore FinTech Festival 2026 booth."
}
```

Response:

```json
{
  "channel": "Event",
  "detail": "Singapore FinTech Festival 2026 — Booth QR Code"
}
```

Allowed channels are exactly:

- `Website`
- `Event`
- `LinkedIn`
- `Organic Search`
- `Referral`
- `Manual/Sales`
- `Other`

The extractor checks recognizable source phrases in the messy `Notes` text and produces a concise detail. Examples include event/booth mentions, LinkedIn DMs/comments, referrals, Google/organic-search language, manual sales entry, and website-form language.

The seed script runs source extraction for all seed rows, so the stored seed data also has `source_channel` and `source_detail` populated.

## Dashboard

### `GET /dashboard`

Returns JSON counts by status and source channel:

```json
{
  "total_leads": 2049,
  "by_status": {
    "New": 270,
    "Contacted": 282
  },
  "by_source_channel": {
    "Event": 374,
    "Website": 507
  }
}
```

A rendered chart/UI is intentionally not included because the assignment only requires a JSON dashboard endpoint.

## Running locally

### 1. Create a virtual environment

Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Seed the database

```bash
python -m scripts.seed_database
```

The script is idempotent by `Record ID`: running it again updates existing seed records rather than creating duplicate seed rows.

### 4. Start the API

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI's interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Running tests

```bash
pytest -q
```

The test suite covers:

- messy value normalization
- date/status/phone normalization
- event/LinkedIn/organic-search/unknown source extraction
- near-duplicate scoring
- blocking behavior
- JSON lead ingestion
- ingestion update behavior for an existing person
- lead search/detail
- dashboard response

## Scope decisions

The following were intentionally not built because the assignment marks them as out of scope:

- authentication/user roles
- website analytics/Google Analytics integration
- general webhook infrastructure
- full audit-log/activity-history UI
- HubSpot migration tooling
- production deployment/scaling/monitoring

The focus is on the requested data modeling, API behavior, deduplication, source extraction, dashboard, and tests.

## What I would do next with more time

1. Add a small review UI for dedupe candidates so a salesperson can accept/reject suggestions.
2. Add a persistent dedupe decision/audit table rather than only returning candidate pairs.
3. Add stronger blocking strategies and benchmark precision/recall against a labeled duplicate set.
4. Add an optional LLM/embedding provider behind a clean interface for harder ambiguous cases, while keeping deterministic fallback behavior.
5. Add structured logging, metrics, authentication, and deployment infrastructure if the system moves toward production.
6. Add database indexes/FTS and pagination strategies if the lead volume grows substantially.

## Assignment checklist

- [x] Load seed CSV into storage
- [x] SQLite-backed lead store
- [x] `GET /leads`
- [x] `GET /leads/:id`
- [x] `PATCH /leads/:id`
- [x] `GET /leads/export`
- [x] `POST /leads/ingest`
- [x] Dedup candidate generation with scalable blocking
- [x] Confidence score and explanation
- [x] No automatic merge required
- [x] Source extraction with allowed channel mapping
- [x] `GET /dashboard`
- [x] Meaningful automated tests
- [x] Run instructions and design decisions documented
- [x] Next-step plan documented
- [x] No paid LLM dependency or API credit cost
