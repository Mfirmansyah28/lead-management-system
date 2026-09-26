from pydantic import BaseModel, ConfigDict, Field, field_validator

class IngestResponse(BaseModel):
    total_rows: int
    inserted: int
    updated: int
    skipped: int
    errors: int
    error_details: list[str]

class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_id: int

    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None

    job_title: str | None = None
    company_name: str | None = None

    email: str | None = None
    email_normalized: str | None = None

    phone_number: str | None = None
    phone_normalized: str | None = None

    country: str | None = None
    city: str | None = None

    lead_status: str | None = None
    lifecycle_stage: str | None = None

    original_source: str | None = None
    original_source_drill_down_1: str | None = None

    contact_owner: str | None = None

    create_date: str | None = None
    last_modified_date: str | None = None

    notes: str | None = None

    annual_revenue: str | None = None
    marketing_contact_status: str | None = None
    gdpr_consent: str | None = None

    lead_score: int | None = None

    name_normalized: str | None = None
    company_normalized: str | None = None

    source_channel: str | None = None
    source_detail: str | None = None


class LeadUpdate(BaseModel):
    status: str | None = None
    owner: str | None = None
    notes: str | None = None

class LeadSummary(BaseModel):
    id: int
    record_id: int

    name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    company_name: str | None = None
    country: str | None = None

class DedupeCandidate(BaseModel):
    lead_a: LeadSummary
    lead_b: LeadSummary

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    reason: str

    signals: list[str]


class DedupeResponse(BaseModel):
    candidate_pairs_considered: int
    candidates: list[DedupeCandidate]


class IngestLead(BaseModel):
    form_id: str | None = None
    form_name: str | None = None
    page_url: str | None = None
    submitted_at: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    country: str | None = None
    message: str | None = None


class SourceExtractionRequest(BaseModel):
    text: str


class SourceExtractionResponse(BaseModel):
    channel: str
    detail: str


class DashboardResponse(BaseModel):
    total_leads: int
    by_status: dict[str, int]
    by_source_channel: dict[str, int]
