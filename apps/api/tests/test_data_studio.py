"""End-to-end API coverage for the Data Studio milestone."""

from datetime import datetime, timedelta
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook


def upload_csv(client: TestClient, content: str, filename: str = "sales.csv") -> dict[str, object]:
    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": (filename, content.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def build_multisheet_xlsx() -> bytes:
    workbook = Workbook()
    north = workbook.active
    north.title = "North"
    north.append(["fecha", "sku", "ventas"])
    north.append(["2025-01-01", "A-01", 12])
    south = workbook.create_sheet("South")
    south.append(["fecha", "sku", "ventas"])
    south.append(["2025-01-02", "B-01", 19])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_upload_valid_csv_and_preview(client: TestClient) -> None:
    dataset = upload_csv(
        client,
        "FECHA_FACTURA,COD_ARTICULO,CANTIDAD,P_UNITARIO\n"
        "2025-01-01,SKU-01,12,9.5\n2025-01-02,SKU-01,15,9.5\n",
    )

    assert dataset["status"] == "inspected"
    assert dataset["row_count"] == 2
    assert dataset["column_count"] == 4
    assert datetime.fromisoformat(str(dataset["imported_at"])).utcoffset() == timedelta(0)
    preview = client.get(f"/api/v1/datasets/{dataset['id']}/preview").json()
    assert preview["total_rows"] == 2
    assert preview["rows"][0]["COD_ARTICULO"] == "SKU-01"


def test_upload_xlsx_and_select_sheet(client: TestClient) -> None:
    response = client.post(
        "/api/v1/datasets/upload",
        files={
            "file": (
                "regional.xlsx",
                build_multisheet_xlsx(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 201
    dataset = response.json()
    assert dataset["status"] == "awaiting_sheet"
    assert dataset["available_sheets"] == ["North", "South"]
    selected = client.post(
        f"/api/v1/datasets/{dataset['id']}/sheet", json={"sheet": "South"}
    )
    assert selected.status_code == 200
    assert selected.json()["selected_sheet"] == "South"
    assert selected.json()["row_count"] == 1


def test_rejects_unsupported_format(client: TestClient) -> None:
    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("payload.exe", b"not tabular", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_format"


def test_detects_date_and_demand_columns(client: TestClient) -> None:
    dataset = upload_csv(
        client,
        "fecha_venta,articulo,cantidad_vendida\n2025-01-01,A,8\n2025-01-02,A,11\n",
    )
    mappings = {item["role"]: item for item in dataset["mappings"]}

    assert mappings["date"]["column_name"] == "fecha_venta"
    assert mappings["date"]["confidence"] >= 0.9
    assert mappings["demand"]["column_name"] == "cantidad_vendida"
    assert mappings["demand"]["confidence"] >= 0.9


def test_saves_and_changes_manual_mapping(client: TestClient) -> None:
    dataset = upload_csv(
        client,
        "periodo,item,units,region\n2025-01-01,A,8,Lima\n2025-01-02,A,11,Lima\n",
    )
    response = client.put(
        f"/api/v1/datasets/{dataset['id']}/mappings",
        json={
            "mappings": [
                {"column_name": "region", "role": "external"},
                {"column_name": "item", "role": "product"},
            ]
        },
    )

    assert response.status_code == 200
    mappings = {item["column_name"]: item for item in response.json()}
    assert mappings["region"]["role"] == "external"
    assert mappings["region"]["source"] == "manual"


def test_accepting_mapping_suggestion_records_confirmation(client: TestClient) -> None:
    dataset = upload_csv(
        client,
        "fecha,sku,ventas\n2025-01-01,A,8\n2025-01-02,A,11\n",
    )
    suggestion = next(item for item in dataset["mappings"] if item["role"] == "date")
    response = client.put(
        f"/api/v1/datasets/{dataset['id']}/mappings",
        json={
            "mappings": [
                {"column_name": suggestion["column_name"], "role": suggestion["role"]}
            ]
        },
    )

    assert response.status_code == 200
    saved = next(
        item for item in response.json() if item["column_name"] == suggestion["column_name"]
    )
    assert saved["source"] == "confirmed"
    assert saved["confidence"] == suggestion["confidence"]


def test_quality_report_detects_missing_duplicate_and_stockout(client: TestClient) -> None:
    dataset = upload_csv(
        client,
        "date,product,demand,stock\n"
        "2025-01-01,A,10,20\n"
        "2025-01-02,A,,18\n"
        "2025-01-02,A,12,17\n"
        "2025-01-03,A,0,0\n"
        "2025-01-04,A,9,10\n",
    )
    response = client.post(f"/api/v1/datasets/{dataset['id']}/validate")

    assert response.status_code == 200, response.text
    assessment = response.json()
    codes = {issue["code"] for issue in assessment["issues"]}
    assert "missing_demand" in codes
    assert "duplicate_dates" in codes
    assert "possible_stockout" in codes
    assert 0 <= assessment["report"]["readiness_score"] <= 100
    assert set(assessment["report"]["component_scores"]) == {
        "structure",
        "temporal_continuity",
        "demand_quality",
        "coverage",
        "product_coverage",
        "context_availability",
    }


def test_mapping_change_invalidates_previous_quality_report(client: TestClient) -> None:
    dataset = upload_csv(
        client,
        "date,demand,stock\n2025-01-01,2,4\n2025-01-02,0,0\n",
    )
    assert client.post(f"/api/v1/datasets/{dataset['id']}/validate").status_code == 200

    mapping = client.put(
        f"/api/v1/datasets/{dataset['id']}/mappings",
        json={"mappings": [{"column_name": "stock", "role": "ignore"}]},
    )

    assert mapping.status_code == 200
    report = client.get(f"/api/v1/datasets/{dataset['id']}/quality-report")
    assert report.status_code == 404
    assert report.json()["error"]["code"] == "report_not_found"


def test_duplicate_exclusive_role_is_rejected(client: TestClient) -> None:
    dataset = upload_csv(
        client,
        "date,product,demand,other\n2025-01-01,A,2,3\n2025-01-02,A,4,5\n",
    )
    response = client.put(
        f"/api/v1/datasets/{dataset['id']}/mappings",
        json={"mappings": [{"column_name": "other", "role": "demand"}]},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "duplicate_role"


def test_demo_dataset_is_reproducible_and_ready_capable(client: TestClient) -> None:
    first = client.post("/api/v1/datasets/demo")
    second = client.post("/api/v1/datasets/demo")

    assert first.status_code == second.status_code == 201
    first_dataset = first.json()
    second_dataset = second.json()
    assert first_dataset["sha256"] == second_dataset["sha256"]
    assert first_dataset["row_count"] == 11_696
    validation = client.post(f"/api/v1/datasets/{first_dataset['id']}/validate")
    assert validation.status_code == 200, validation.text
    assessment = validation.json()
    assert assessment["report"]["frequency"] == "daily"
    assert assessment["report"]["duration_days"] == 731
    assert assessment["report"]["has_critical_errors"] is False
    assert any(issue["code"] == "possible_stockout" for issue in assessment["issues"])
    ready = client.post(f"/api/v1/datasets/{first_dataset['id']}/ready")
    assert ready.status_code == 200
    assert ready.json()["dataset"]["status"] == "ready"


def test_health_remains_available_with_data_studio(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
