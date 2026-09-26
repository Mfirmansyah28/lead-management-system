import re
import unicodedata
from datetime import datetime

STATUS_MAP = {
    "new": "New",
    "contacted": "Contacted",
    "connected": "Connected",
    "qualified": "Qualified",
    "opportunity": "Opportunity",
    "close won": "Closed Won",
    "closed won": "Closed Won",
    "closed lost": "Closed Lost",
}

def clean_text(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    return re.sub(r"\s+"," ", value)

def normalize_email(value: str | None) -> str | None:
    value = clean_text(value)

    if value is None:
        return None

    return value.lower()

def normalize_phone(value: str | None) -> str | None:
    value = clean_text(value)

    if value is None:
        return None

    digits = re.sub(r"\D", "", value)

    return digits or None

def normalize_name(value: str | None) -> str | None:
    value = clean_text(value)

    if value is None:
        return None

    value = unicodedata.normalize("NFKC", value)
    value = value.casefold()

    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip() or None


def normalize_company(value: str | None) -> str | None:
    value = clean_text(value)

    if value is None:
        return None

    value = unicodedata.normalize("NFKC", value)
    value = value.casefold()

    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip() or None


def normalize_status(value: str | None) -> str | None:
    value = clean_text(value)

    if value is None:
        return None

    return STATUS_MAP.get(value.casefold(), value)


def normalize_date(value: str | None) -> str | None:
    value = clean_text(value)

    if value is None:
        return None

    try:
        if "T" in value:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        elif "/" in value:
            parsed = datetime.strptime(value, "%m/%d/%Y")
        else:
            parsed = datetime.strptime(value, "%Y-%m-%d")

        return parsed.isoformat()

    except ValueError:
        return value

def split_name(value: str | None) -> tuple[str | None, str | None]:
    value = clean_text(value)
    if not value:
        return None, None
    parts = value.split(" ", 1)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]
