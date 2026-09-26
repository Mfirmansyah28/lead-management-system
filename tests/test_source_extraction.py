from app.services.source_extraction import extract_source


def test_event_source_with_qr_code():
    result = extract_source("Scanned the QR code at our Singapore FinTech Festival 2026 booth.")
    assert result.channel == "Event"
    assert "Singapore FinTech Festival 2026" in result.detail
    assert "QR Code" in result.detail


def test_linkedin_dm_source():
    result = extract_source("Linkedin dm inbound asking about pricing.")
    assert result.channel == "LinkedIn"
    assert result.detail == "LinkedIn DM"


def test_organic_search_source():
    result = extract_source("Found us through organic google search then landed on the book-a-demo page.")
    assert result.channel == "Organic Search"


def test_unknown_source_is_other():
    result = extract_source("Walked into the office without an appointment.")
    assert result.channel == "Other"
