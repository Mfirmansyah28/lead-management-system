from pydantic import BaseModel, ConfigDict

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