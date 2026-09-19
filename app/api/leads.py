import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Lead
from app.schemas.lead import LeadResponse, LeadUpdate
from app.services.normalization import normalize_status


router = APIRouter(
    prefix="/leads",
    tags=["Leads"],
)


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


@router.get(
    "/",
    response_model=list[LeadResponse],
)
def list_leads(
    status: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    country: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
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

    statement = statement.offset(offset).limit(limit)

    leads = db.scalars(statement).all()

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

    statement = statement.order_by(Lead.id)

    leads = db.scalars(statement).all()

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow(EXPORT_FIELDS)

    for lead in leads:
        writer.writerow(
            [
                getattr(lead, field)
                for field in EXPORT_FIELDS
            ]
        )

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; filename=leads_export.csv"
            )
        },
    )


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
):
    statement = select(Lead).where(
        Lead.id == lead_id
    )

    lead = db.scalar(statement)

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
    statement = select(Lead).where(
        Lead.id == lead_id
    )

    lead = db.scalar(statement)

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

        lead.lead_status = updates["status"]

    if "owner" in updates:
        lead.contact_owner = updates["owner"]

    if "notes" in updates:
        lead.notes = updates["notes"]

    db.commit()
    db.refresh(lead)

    return lead


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