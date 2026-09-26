from app.services.normalization import normalize_date, normalize_name, normalize_phone, normalize_status


def test_normalization_handles_messy_values():
    assert normalize_status("  NEW ") == "New"
    assert normalize_phone("+1 (555) 123-4567") == "15551234567"
    assert normalize_name("Acme,  Jane") == "acme jane"
    assert normalize_date("6/4/2026") == "2026-06-04T00:00:00"
