from app.db.models import Lead
from app.services.dedup import score_pair, generate_candidate_pairs


def make_lead(id_, name, email, phone, company, country="Singapore"):
    return Lead(
        id=id_, record_id=id_, full_name=name,
        email=email, email_normalized=email.lower(),
        phone_number=phone, phone_normalized=phone,
        company_name=company, company_normalized=company.lower(),
        country=country, name_normalized=name.lower(),
    )


def test_near_duplicate_gets_high_confidence():
    a = make_lead(1, "Jane Tan", "jane.tan@acme.com", "6591234567", "Acme Pte Ltd")
    b = make_lead(2, "Jane Tann", "jane.tan@acme.com", "6591234567", "Acme Pte. Ltd")
    confidence, scores = score_pair(a, b)
    assert confidence >= 0.98
    assert scores["email"] == 1.0


def test_blocking_avoids_unrelated_pairs():
    leads = [
        make_lead(1, "Jane Tan", "jane@acme.com", "11111111", "Acme"),
        make_lead(2, "John Doe", "john@example.org", "22222222", "Example"),
        make_lead(3, "Jane Tann", "jane@acme.com", "11111111", "Acme"),
    ]
    pairs = generate_candidate_pairs(leads)
    assert (1, 3) in pairs
    assert (1, 2) not in pairs
