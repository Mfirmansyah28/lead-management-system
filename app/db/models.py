from sqlalchemy import Integer, String
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

    phone_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    lead_status: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
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