from collections import defaultdict
from itertools import combinations

from rapidfuzz import fuzz

from app.db.models import Lead


MAX_BLOCK_SIZE = 50

GENERIC_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "proton.me",
}


def get_lead_name(lead: Lead) -> str | None:
    if lead.name_normalized:
        return lead.name_normalized

    parts = [
        lead.first_name,
        lead.last_name,
    ]

    value = " ".join(
        part.strip()
        for part in parts
        if part and part.strip()
    )

    return value.lower() or None


def get_email_domain(
    email: str | None,
) -> str | None:
    if not email or "@" not in email:
        return None

    return email.rsplit("@", 1)[1].lower()


def build_block_keys(lead: Lead) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []

    if lead.phone_normalized:
        keys.append(
            ("phone", lead.phone_normalized)
        )

    if lead.email_normalized:
        keys.append(
            ("email", lead.email_normalized)
        )

        domain = get_email_domain(
            lead.email_normalized
        )

        if (
            domain
            and domain not in GENERIC_EMAIL_DOMAINS
        ):
            keys.append(
                ("email_domain", domain)
            )

    if lead.company_normalized:
        keys.append(
            ("company", lead.company_normalized)
        )

    name = get_lead_name(lead)

    if name:
        keys.append(
            ("name", name)
        )

        if lead.country:
            keys.append(
                (
                    "name_country",
                    f"{name}|{lead.country.lower().strip()}",
                )
            )

    return keys


def generate_candidate_pairs(
    leads: list[Lead],
) -> set[tuple[int, int]]:
    blocks: dict[
        tuple[str, str],
        set[int],
    ] = defaultdict(set)

    lead_by_id = {
        lead.id: lead
        for lead in leads
    }

    for lead in leads:
        for block_key in build_block_keys(lead):
            blocks[block_key].add(lead.id)

    pairs: set[tuple[int, int]] = set()

    for block_lead_ids in blocks.values():
        if len(block_lead_ids) < 2:
            continue

        if len(block_lead_ids) > MAX_BLOCK_SIZE:
            continue

        for lead_a_id, lead_b_id in combinations(
            sorted(block_lead_ids),
            2,
        ):
            pairs.add(
                (lead_a_id, lead_b_id)
            )

    # Make sure generated IDs actually exist.
    return {
        (lead_a_id, lead_b_id)
        for lead_a_id, lead_b_id in pairs
        if lead_a_id in lead_by_id
        and lead_b_id in lead_by_id
    }


def email_similarity(
    email_a: str | None,
    email_b: str | None,
) -> float:
    if not email_a or not email_b:
        return 0.0

    if email_a == email_b:
        return 1.0

    if "@" not in email_a or "@" not in email_b:
        return 0.0

    local_a, domain_a = email_a.rsplit(
        "@",
        1,
    )

    local_b, domain_b = email_b.rsplit(
        "@",
        1,
    )

    local_score = fuzz.ratio(
        local_a,
        local_b,
    ) / 100

    domain_score = fuzz.ratio(
        domain_a,
        domain_b,
    ) / 100

    return (
        local_score * 0.65
        + domain_score * 0.35
    )


def phone_similarity(
    phone_a: str | None,
    phone_b: str | None,
) -> float:
    if not phone_a or not phone_b:
        return 0.0

    if phone_a == phone_b:
        return 1.0

    if (
        len(phone_a) >= 8
        and len(phone_b) >= 8
        and phone_a[-8:] == phone_b[-8:]
    ):
        return 0.9

    return 0.0


def text_similarity(
    value_a: str | None,
    value_b: str | None,
) -> float:
    if not value_a or not value_b:
        return 0.0

    return (
        fuzz.token_set_ratio(
            value_a,
            value_b,
        )
        / 100
    )


def score_pair(
    lead_a: Lead,
    lead_b: Lead,
) -> tuple[float, dict[str, float]]:
    name_score = text_similarity(
        get_lead_name(lead_a),
        get_lead_name(lead_b),
    )

    company_score = text_similarity(
        lead_a.company_normalized,
        lead_b.company_normalized,
    )

    email_score = email_similarity(
        lead_a.email_normalized,
        lead_b.email_normalized,
    )

    phone_score = phone_similarity(
        lead_a.phone_normalized,
        lead_b.phone_normalized,
    )

    country_score = (
        1.0
        if (
            lead_a.country
            and lead_b.country
            and lead_a.country.strip().casefold()
            == lead_b.country.strip().casefold()
        )
        else 0.0
    )

    score = (
        name_score * 0.35
        + company_score * 0.20
        + email_score * 0.20
        + phone_score * 0.20
        + country_score * 0.05
    )

    # Exact contact identifiers receive stronger confidence
    # when they agree with at least one other identity signal.
    if (
        lead_a.email_normalized
        and lead_b.email_normalized
        and lead_a.email_normalized
        == lead_b.email_normalized
        and (
            name_score >= 0.50
            or company_score >= 0.50
        )
    ):
        score = max(score, 0.98)

    elif (
        lead_a.phone_normalized
        and lead_b.phone_normalized
        and lead_a.phone_normalized
        == lead_b.phone_normalized
        and (
            name_score >= 0.50
            or company_score >= 0.50
        )
    ):
        score = max(score, 0.96)

    return min(score, 1.0), {
        "name": name_score,
        "company": company_score,
        "email": email_score,
        "phone": phone_score,
        "country": country_score,
    }


def build_reason(
    lead_a: Lead,
    lead_b: Lead,
    scores: dict[str, float],
) -> tuple[str, list[str]]:
    signals: list[str] = []

    if (
        lead_a.email_normalized
        and lead_b.email_normalized
        and lead_a.email_normalized
        == lead_b.email_normalized
    ):
        signals.append(
            "exact normalized email match"
        )

    if (
        lead_a.phone_normalized
        and lead_b.phone_normalized
        and lead_a.phone_normalized
        == lead_b.phone_normalized
    ):
        signals.append(
            "exact normalized phone match"
        )

    if scores["name"] >= 0.90:
        signals.append(
            "very similar names"
        )

    elif scores["name"] >= 0.75:
        signals.append(
            "similar names"
        )

    if scores["company"] >= 0.90:
        signals.append(
            "very similar company names"
        )

    elif scores["company"] >= 0.75:
        signals.append(
            "similar company names"
        )

    if scores["email"] >= 0.80:
        signals.append(
            "similar email addresses"
        )

    if scores["phone"] >= 0.80:
        signals.append(
            "similar phone numbers"
        )

    if scores["country"] == 1.0:
        signals.append(
            "same country"
        )

    if not signals:
        signals.append(
            "multiple identity fields are similar"
        )

    reason = "; ".join(signals)

    return reason, signals