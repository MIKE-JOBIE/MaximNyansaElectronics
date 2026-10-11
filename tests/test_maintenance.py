def test_maintenance_endpoint_requires_configured_secret_and_valid_header(app, client):
    assert client.post("/health/maintenance/release-stale").status_code == 503

    app.config["MAINTENANCE_SECRET"] = "test-maintenance-secret"
    assert client.post("/health/maintenance/release-stale").status_code == 401

    response = client.post(
        "/health/maintenance/release-stale",
        headers={"X-Maintenance-Secret": "test-maintenance-secret"},
    )
    assert response.status_code == 200
    assert response.get_json()["released_orders"] == 0
