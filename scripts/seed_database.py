import csv
from pathlib import Path

from app.db.database import Base, SessionLocal, engine
from app.db.models import Lead
from app.services.source_extraction import extract_source
from app.services.normalization import (
    clean_text,
    normalize_company,
    normalize_date,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_status,
)


BASE_DIR = Path(__file__).resolve().parents[1]

CSV_PATH = BASE_DIR / "data" / "leads_seed.csv"


COLUMN_MAP = {
    "Record ID": "record_id",
    "First Name": "first_name",
    "Last Name": "last_name",
    "Full Name": "full_name",
    "Job Title": "job_title",
    "Company Name": "company_name",
    "Email": "email",
    "Phone Number": "phone_number",
    "Country/Region": "country",
    "City": "city",
    "Lead Status": "lead_status",
    "Lifecycle Stage": "lifecycle_stage",
    "Original Source": "original_source",
    "Original Source Drill-Down 1": "original_source_drill_down_1",
    "Contact Owner": "contact_owner",
    "Create Date": "create_date",
    "Last Modified Date": "last_modified_date",
    "Notes": "notes",
    "Annual Revenue": "annual_revenue",
    "Marketing contact status": "marketing_contact_status",
    "GDPR consent": "gdpr_consent",
    "Lead Score": "lead_score",
}


def parse_nullable_int(value: str | None) -> int | None:
    value = clean_text(value)

    if value is None:
        return None

    try:
        return int(float(value))
    except ValueError:
        return None


def normalize_row(row: dict[str, str]) -> dict:
    data = {
        db_field: clean_text(row[csv_field])
        for csv_field, db_field in COLUMN_MAP.items()
    }

    data["record_id"] = int(row["Record ID"])

    data["email"] = normalize_email(row["Email"])
    data["phone_number"] = clean_text(row["Phone Number"])

    data["lead_status"] = normalize_status(row["Lead Status"])

    data["create_date"] = normalize_date(row["Create Date"])
    data["last_modified_date"] = normalize_date(
        row["Last Modified Date"]
    )

    data["lead_score"] = parse_nullable_int(row["Lead Score"])

    data["email_normalized"] = normalize_email(row["Email"])

    data["phone_normalized"] = normalize_phone(
        row["Phone Number"]
    )

    first_name = clean_text(row["First Name"])
    last_name = clean_text(row["Last Name"])
    full_name = clean_text(row["Full Name"])

    if full_name:
        name_for_matching = full_name
    else:
        name_for_matching = " ".join(
            part for part in [first_name, last_name] if part
        )

    data["name_normalized"] = normalize_name(
        name_for_matching
    )

    data["company_normalized"] = normalize_company(
        row["Company Name"]
    )

    source = extract_source(row.get("Notes"))
    data["source_channel"] = source.channel
    data["source_detail"] = source.detail

    return data


def seed_database() -> None:
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()

    inserted = 0
    updated = 0

    try:
        with CSV_PATH.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                data = normalize_row(row)

                lead = (
                    session.query(Lead)
                    .filter(Lead.record_id == data["record_id"])
                    .first()
                )

                if lead is None:
                    lead = Lead(**data)
                    session.add(lead)
                    inserted += 1
                else:
                    for field, value in data.items():
                        setattr(lead, field, value)

                    updated += 1

        session.commit()

        print(f"Inserted: {inserted}")
        print(f"Updated: {updated}")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    seed_database()