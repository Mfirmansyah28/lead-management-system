import csv
from io import StringIO
from types import SimpleNamespace

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    File,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Lead
from app.schemas.lead import (
    DedupeCandidate,
    DedupeResponse,
    IngestResponse,
    LeadResponse,
    LeadSummary,
    LeadUpdate,
    IngestLead,
    SourceExtractionRequest,
    SourceExtractionResponse,
    DashboardResponse,
)
from app.services.dedup import (
    build_reason,
    generate_candidate_pairs,
    score_pair,
)
from app.services.normalization import (
    clean_text,
    normalize_company,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_status,
    split_name,
)
from app.services.source_extraction import extract_source


router = APIRouter(
    prefix="/leads",
    tags=["Leads"],
)


EXPORT_FIELDS = [
    "id",
    "record_id",
    "first_name",
    "last_name",
    "full_name",
    "job_title",
    "company_name",
    "email",
    "phone_number",
    "country",
    "city",
    "lead_status",
    "lifecycle_stage",
    "original_source",
    "original_source_drill_down_1",
    "contact_owner",
    "create_date",
    "last_modified_date",
    "notes",
    "annual_revenue",
    "marketing_contact_status",
    "gdpr_consent",
    "lead_score",
    "source_channel",
    "source_detail",
]


def apply_filters(
    statement,
    status: str | None,
    owner: str | None,
    country: str | None,
    q: str | None,
):
    if status:
        normalized_status = normalize_status(status)

        statement = statement.where(
            Lead.lead_status == normalized_status
        )

    if owner:
        statement = statement.where(
            Lead.contact_owner.ilike(
                f"%{owner.strip()}%"
            )
        )

    if country:
        statement = statement.where(
            Lead.country.ilike(
                f"%{country.strip()}%"
            )
        )

    if q:
        search = f"%{q.strip()}%"

        statement = statement.where(
            or_(
                Lead.full_name.ilike(search),
                Lead.first_name.ilike(search),
                Lead.last_name.ilike(search),
                Lead.company_name.ilike(search),
                Lead.email.ilike(search),
                Lead.name_normalized.ilike(search),
                Lead.company_normalized.ilike(search),
                Lead.email_normalized.ilike(search),
            )
        )

    return statement


def make_lead_summary(
    lead: Lead,
) -> LeadSummary:
    name = (
        lead.full_name
        or " ".join(
            part
            for part in [
                lead.first_name,
                lead.last_name,
            ]
            if part
        )
        or None
    )

    return LeadSummary(
        id=lead.id,
        record_id=lead.record_id,
        name=name,
        email=lead.email,
        phone_number=lead.phone_number,
        company_name=lead.company_name,
        country=lead.country,
    )


@router.get(
    "/",
    response_model=list[LeadResponse],
)
def list_leads(
    status: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    country: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
):
    statement = select(Lead)

    statement = apply_filters(
        statement,
        status=status,
        owner=owner,
        country=country,
        q=q,
    )

    statement = statement.order_by(Lead.id)

    statement = statement.offset(
        offset
    ).limit(
        limit
    )

    leads = db.scalars(
        statement
    ).all()

    return leads


@router.get(
    "/export",
)
def export_leads(
    status: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    country: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    statement = select(Lead)

    statement = apply_filters(
        statement,
        status=status,
        owner=owner,
        country=country,
        q=q,
    )

    statement = statement.order_by(
        Lead.id
    )

    leads = db.scalars(
        statement
    ).all()

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow(
        EXPORT_FIELDS
    )

    for lead in leads:
        writer.writerow(
            [
                getattr(
                    lead,
                    field,
                )
                for field in EXPORT_FIELDS
            ]
        )

    output.seek(0)

    return StreamingResponse(
        iter(
            [output.getvalue()]
        ),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; "
                "filename=leads_export.csv"
            )
        },
    )


@router.post(
    "/dedupe-candidates",
    response_model=DedupeResponse,
)
def find_dedupe_candidates(
    min_confidence: float = Query(
        default=0.72,
        ge=0.0,
        le=1.0,
    ),
    db: Session = Depends(get_db),
):
    leads = db.scalars(
        select(Lead)
    ).all()

    lead_by_id = {
        lead.id: lead
        for lead in leads
    }

    candidate_pairs = (
        generate_candidate_pairs(
            leads
        )
    )

    candidates: list[DedupeCandidate] = []

    for lead_a_id, lead_b_id in candidate_pairs:
        lead_a = lead_by_id[
            lead_a_id
        ]

        lead_b = lead_by_id[
            lead_b_id
        ]

        confidence, scores = score_pair(
            lead_a,
            lead_b,
        )

        if confidence < min_confidence:
            continue

        reason, signals = build_reason(
            lead_a,
            lead_b,
            scores,
        )

        candidates.append(
            DedupeCandidate(
                lead_a=make_lead_summary(
                    lead_a
                ),
                lead_b=make_lead_summary(
                    lead_b
                ),
                confidence=round(
                    confidence,
                    4,
                ),
                reason=reason,
                signals=signals,
            )
        )

    candidates.sort(
        key=lambda candidate: candidate.confidence,
        reverse=True,
    )

    return DedupeResponse(
        candidate_pairs_considered=len(
            candidate_pairs
        ),
        candidates=candidates,
    )


@router.post(
    "/ingest",
    response_model=IngestResponse,
)
def ingest_leads(
    payload: IngestLead | list[IngestLead],
    db: Session = Depends(get_db),
):
    """Ingest website-form submissions in the assignment's JSON shape."""
    submissions: list[IngestLead] = payload if isinstance(payload, list) else [payload]

    inserted = updated = skipped = errors = 0
    error_details: list[str] = []

    existing_leads = db.scalars(select(Lead)).all()
    next_record_id = (db.scalar(select(Lead.record_id).order_by(Lead.record_id.desc()).limit(1)) or 0) + 1

    def find_existing(submission: IngestLead) -> Lead | None:
        email = normalize_email(submission.email)
        phone = normalize_phone(submission.phone)
        company = normalize_company(submission.company)
        name = normalize_name(submission.name)

        if email:
            lead = db.scalar(select(Lead).where(Lead.email_normalized == email))
            if lead:
                return lead
        if phone:
            lead = db.scalar(select(Lead).where(Lead.phone_normalized == phone))
            if lead:
                return lead

        # Candidate generation is deliberately blocked by normalized identity fields.
        candidates = [
            lead for lead in existing_leads
            if (company and lead.company_normalized == company)
            or (name and lead.name_normalized == name)
        ]
        best: tuple[float, Lead] | None = None
        probe = SimpleNamespace(
            id=-1,
            record_id=-1,
            full_name=clean_text(submission.name),
            first_name=None,
            last_name=None,
            company_name=clean_text(submission.company),
            email=clean_text(submission.email),
            phone_number=clean_text(submission.phone),
            country=clean_text(submission.country),
            name_normalized=name,
            company_normalized=company,
            email_normalized=email,
            phone_normalized=phone,
        )
        for lead in candidates:
            confidence, _ = score_pair(probe, lead)
            if confidence >= 0.90 and (best is None or confidence > best[0]):
                best = (confidence, lead)
        return best[1] if best else None

    for index, submission in enumerate(submissions, start=1):
        try:
            if not any([
                submission.name, submission.email, submission.phone,
                submission.company,
            ]):
                skipped += 1
                error_details.append(f"Item {index}: no identifying fields")
                continue

            source = extract_source(submission.message)
            existing = find_existing(submission)
            first_name, last_name = split_name(submission.name)

            if existing:
                existing.first_name = first_name or existing.first_name
                existing.last_name = last_name or existing.last_name
                existing.full_name = clean_text(submission.name) or existing.full_name
                existing.company_name = clean_text(submission.company) or existing.company_name
                existing.email = clean_text(submission.email) or existing.email
                existing.email_normalized = normalize_email(submission.email) or existing.email_normalized
                existing.phone_number = clean_text(submission.phone) or existing.phone_number
                existing.phone_normalized = normalize_phone(submission.phone) or existing.phone_normalized
                existing.country = clean_text(submission.country) or existing.country
                existing.notes = clean_text(submission.message) or existing.notes
                existing.source_channel = source.channel
                existing.source_detail = source.detail
                existing.original_source = "Website Form"
                updated += 1
            else:
                lead = Lead(
                    record_id=next_record_id,
                    first_name=first_name,
                    last_name=last_name,
                    full_name=clean_text(submission.name),
                    company_name=clean_text(submission.company),
                    email=clean_text(submission.email),
                    email_normalized=normalize_email(submission.email),
                    phone_number=clean_text(submission.phone),
                    phone_normalized=normalize_phone(submission.phone),
                    country=clean_text(submission.country),
                    lead_status="New",
                    original_source="Website Form",
                    original_source_drill_down_1=clean_text(submission.page_url),
                    create_date=clean_text(submission.submitted_at),
                    last_modified_date=clean_text(submission.submitted_at),
                    notes=clean_text(submission.message),
                    name_normalized=normalize_name(submission.name),
                    company_normalized=normalize_company(submission.company),
                    source_channel=source.channel,
                    source_detail=source.detail,
                )
                db.add(lead)
                existing_leads.append(lead)
                next_record_id += 1
                inserted += 1

        except Exception as exc:
            errors += 1
            error_details.append(f"Item {index}: {exc}")

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return IngestResponse(
        total_rows=len(submissions),
        inserted=inserted,
        updated=updated,
        skipped=skipped,
        errors=errors,
        error_details=error_details,
    )


@router.post("/ingest-csv", response_model=IngestResponse)
async def ingest_csv_legacy(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Convenience CSV ingestion; the required assignment endpoint is /leads/ingest."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file is required")
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV file must use UTF-8 encoding") from exc
    rows = list(csv.DictReader(StringIO(text)))
    payload = [IngestLead(
        name=row.get("Full Name") or " ".join(x for x in [row.get("First Name"), row.get("Last Name")] if x),
        email=row.get("Email"), phone=row.get("Phone Number"), company=row.get("Company Name"),
        country=row.get("Country/Region"), message=row.get("Notes"),
        submitted_at=row.get("Create Date"),
    ) for row in rows]
    return ingest_leads(payload, db)


@router.post(
    "/source-extract",
    response_model=SourceExtractionResponse,
)
def source_extract(payload: SourceExtractionRequest):
    result = extract_source(payload.text)
    return SourceExtractionResponse(
        channel=result.channel,
        detail=result.detail,
    )


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
)
def dashboard(db: Session = Depends(get_db)):
    leads = db.scalars(select(Lead)).all()
    by_status: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for lead in leads:
        status = lead.lead_status or "Unknown"
        source = lead.source_channel or "Unknown"
        by_status[status] = by_status.get(status, 0) + 1
        by_source[source] = by_source.get(source, 0) + 1
    return DashboardResponse(
        total_leads=len(leads),
        by_status=dict(sorted(by_status.items())),
        by_source_channel=dict(sorted(by_source.items())),
    )


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
):
    statement = select(
        Lead
    ).where(
        Lead.id == lead_id
    )

    lead = db.scalar(
        statement
    )

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    return lead


@router.patch(
    "/{lead_id}",
    response_model=LeadResponse,
)
def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
):
    statement = select(
        Lead
    ).where(
        Lead.id == lead_id
    )

    lead = db.scalar(
        statement
    )

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No fields to update",
        )

    if "status" in updates:
        updates["status"] = normalize_status(
            updates["status"]
        )

        lead.lead_status = updates[
            "status"
        ]

    if "owner" in updates:
        lead.contact_owner = updates[
            "owner"
        ]

    if "notes" in updates:
        lead.notes = updates[
            "notes"
        ]

    db.commit()

    db.refresh(lead)

    return lead