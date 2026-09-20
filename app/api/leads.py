import csv
from io import StringIO

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile
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
)
from app.services.dedup import (
    build_reason,
    generate_candidate_pairs,
    score_pair,
)
from app.services.normalization import normalize_status


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
async def ingest_leads(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is required",
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported",
        )

    content = await file.read()

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="CSV file must use UTF-8 encoding",
        )

    reader = csv.DictReader(
        StringIO(text)
    )

    if not reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="CSV file has no header",
        )

    required_fields = {
        "Record ID",
    }

    missing_fields = (
        required_fields
        - set(reader.fieldnames)
    )

    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=(
                "Missing required columns: "
                + ", ".join(
                    sorted(missing_fields)
                )
            ),
        )

    total_rows = 0
    inserted = 0
    updated = 0
    skipped = 0
    errors = 0
    error_details: list[str] = []

    for row_number, row in enumerate(
        reader,
        start=2,
    ):
        total_rows += 1

        try:
            record_id_value = (
                row.get("Record ID")
                or ""
            ).strip()

            if not record_id_value:
                skipped += 1

                error_details.append(
                    f"Row {row_number}: missing Record ID"
                )

                continue

            record_id = int(
                record_id_value
            )

            existing = db.scalar(
                select(Lead).where(
                    Lead.record_id
                    == record_id
                )
            )

            if existing:
                updated += 1
            else:
                inserted += 1

        except (ValueError, TypeError) as exc:
            errors += 1

            error_details.append(
                f"Row {row_number}: {exc}"
            )

    return IngestResponse(
        total_rows=total_rows,
        inserted=inserted,
        updated=updated,
        skipped=skipped,
        errors=errors,
        error_details=error_details,
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