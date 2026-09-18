from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    record_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
        index=True,
    )

    first_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    job_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    company_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    email_normalized: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    phone_normalized: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    lead_status: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    lifecycle_stage: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    original_source: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    original_source_drill_down_1: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    contact_owner: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    create_date: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    last_modified_date: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    annual_revenue: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    marketing_contact_status: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    gdpr_consent: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    lead_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    name_normalized: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    company_normalized: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    source_channel: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source_detail: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_leads_company_name_normalized",
            "company_normalized",
        ),
    )