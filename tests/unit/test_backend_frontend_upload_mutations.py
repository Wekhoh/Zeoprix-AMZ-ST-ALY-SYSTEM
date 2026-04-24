from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient

from src.backend.app import create_app
from src.data.db import Database


def _bootstrap(monkeypatch, tmp_path):
    legacy_db_path = tmp_path / "legacy-upload.db"
    monkeypatch.setenv("DATABASE_PATH", str(legacy_db_path))
    monkeypatch.setenv(
        "AMZ_BACKEND_DATABASE_URL",
        f"sqlite:///{(tmp_path / 'backend-upload.db').as_posix()}",
    )
    db = Database(str(legacy_db_path))
    db.init_schema()
    db.init_default_rules()
    product_id = db.create_product(name="真实产品", asin="B0TEST12345", category="Home")
    db.close()
    return product_id


def test_frontend_upload_files_endpoint_saves_rows_and_can_analyze(
    monkeypatch, tmp_path
):
    product_id = _bootstrap(monkeypatch, tmp_path)
    csv_content = (
        "Customer Search Term,Impressions,Clicks,Spend,7 Day Total Orders (#),7 Day Total Sales\n"
        "travel pillow,120,25,18.5,2,42.0\n"
    ).encode("utf-8")

    with TestClient(create_app()) as client:
        response = client.post(
            "/frontend/upload/files",
            data={"product_id": str(product_id), "auto_analyze": "true"},
            files=[("files", ("Auto Campaign.csv", BytesIO(csv_content), "text/csv"))],
        )

    assert response.status_code == 200
    body = response.json()
    assert body["campaignsCreated"] == 1
    assert body["importedRows"] == 1
    assert body["failedFiles"] == []
    assert body["analysisState"]["status"] in {"success", "warning"}


def test_frontend_upload_files_endpoint_reports_failures(monkeypatch, tmp_path):
    product_id = _bootstrap(monkeypatch, tmp_path)
    invalid_csv = b"Customer Search Term,Impressions\n"

    with TestClient(create_app()) as client:
        response = client.post(
            "/frontend/upload/files",
            data={"product_id": str(product_id), "auto_analyze": "false"},
            files=[
                ("files", ("Broken Campaign.csv", BytesIO(invalid_csv), "text/csv"))
            ],
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "warning"
    assert body["campaignsCreated"] == 0
    assert body["importedRows"] == 0
    assert body["failedFiles"][0]["fileName"] == "Broken Campaign.csv"
