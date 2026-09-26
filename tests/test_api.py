def test_leads_filter_and_detail(client):
    response = client.post("/leads/ingest", json={
        "name": "API Test Person",
        "email": "api-test@example.com",
        "phone": "+65 9000 1111",
        "company": "API Test Co",
        "country": "Singapore",
        "message": "Found us through organic google search.",
    })
    assert response.status_code == 200
    assert response.json()["inserted"] == 1

    rows = client.get("/leads/", params={"q": "api-test@example.com"})
    assert rows.status_code == 200
    assert len(rows.json()) == 1
    lead_id = rows.json()[0]["id"]

    detail = client.get(f"/leads/{lead_id}")
    assert detail.status_code == 200
    assert detail.json()["source_channel"] == "Organic Search"


def test_ingest_updates_existing_person(client):
    first = client.post("/leads/ingest", json={
        "name": "Same Person",
        "email": "same@example.com",
        "company": "Example Co",
        "country": "Singapore",
        "message": "Referral from a partner.",
    })
    assert first.json()["inserted"] == 1

    second = client.post("/leads/ingest", json={
        "name": "Same Person",
        "email": "same@example.com",
        "company": "Example Co",
        "country": "Singapore",
        "message": "Manual - added after inbound phone call.",
    })
    assert second.json()["updated"] == 1
    assert second.json()["inserted"] == 0


def test_dashboard_returns_status_and_source_counts(client):
    client.post("/leads/ingest", json={
        "name": "Dashboard Person",
        "email": "dashboard@example.com",
        "company": "Dashboard Co",
        "message": "Linkedin dm inbound asking about pricing.",
    })
    response = client.get("/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "by_status" in data
    assert "by_source_channel" in data
