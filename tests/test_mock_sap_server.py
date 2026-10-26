"""Unit tests for SAP Upper Line Mock Service (mock_sap_server.py)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi.testclient import TestClient

from mock_sap_server import (
    DEFAULT_SAP_TOKEN,
    app,
    clear_history_records,
    generate_accounting_log,
)

client = TestClient(app)
AUTH_HEADER_KEY = {"X-Odoo-API-Key": DEFAULT_SAP_TOKEN}
AUTH_HEADER_BEARER = {"Authorization": f"Bearer {DEFAULT_SAP_TOKEN}"}


@pytest.fixture(autouse=True)
def reset_history():
    """Ensures in-memory history is cleared before each test."""
    clear_history_records()
    yield
    clear_history_records()


def test_root_and_health_endpoints():
    """Verifies public healthcheck endpoints return status ok and metadata."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    data_root = res_root.json()
    assert data_root["status"] == "ok"
    assert data_root["service"] == "Mock SAP Service"
    assert data_root["version"] == "1.0.0"

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json() == data_root


def test_docs_and_openapi_availability():
    """Verifies Swagger UI and OpenAPI documentation schema endpoints are accessible."""
    res_docs = client.get("/docs")
    assert res_docs.status_code == 200

    res_redoc = client.get("/redoc")
    assert res_redoc.status_code == 200

    res_openapi = client.get("/openapi.json")
    assert res_openapi.status_code == 200
    openapi_data = res_openapi.json()
    assert "paths" in openapi_data
    assert "/api/sap/goods-receipt" in openapi_data["paths"]
    assert "/api/sap/goods-issue" in openapi_data["paths"]


def test_unauthorized_access_rejection():
    """Verifies missing or invalid API keys are strictly rejected with HTTP 401."""
    # Missing headers
    res_no_auth = client.post("/api/sap/goods-receipt", json={})
    assert res_no_auth.status_code == 401
    err_json = res_no_auth.json()
    assert err_json["status"] == "ERROR"
    assert err_json["code"] == 401
    assert "Unauthorized" in err_json["message"]

    # Invalid header token
    res_bad_auth = client.post(
        "/api/sap/goods-receipt",
        json={},
        headers={"X-Odoo-API-Key": "wrong_token"},
    )
    assert res_bad_auth.status_code == 401


def test_goods_receipt_webhook_simulation():
    """Verifies Goods Receipt webhook posts simulated GL journal entry."""
    payload = {
        "sap_doc_number": "PO-SAP-2026-001",
        "status": "GOODS_RECEIVED",
        "received_date": "2026-10-23T11:00:00Z",
        "warehouse_code": "WH-JKT-01",
    }
    # Test via X-Odoo-API-Key header
    res = client.post("/api/sap/goods-receipt", json=payload, headers=AUTH_HEADER_KEY)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["code"] == 200
    assert "Goods Receipt posted into SAP General Ledger" in data["message"]

    acct = data["sap_accounting_log"]
    assert acct["journal_entry"].startswith("JE-SAP-2026-")
    assert acct["posting_date"] == "2026-10-23"
    assert "101.001 - Persediaan Barang Masuk" in acct["debit_account"]
    assert "201.001 - Hutang Dagang Belum Difakturkan" in acct["credit_account"]
    assert acct["vat_in_11%"] == "Rp 5.500.000"
    assert acct["financial_status"] == "POSTED"

    # Verify history recorded
    hist_res = client.get("/api/sap/history", headers=AUTH_HEADER_BEARER)
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["count"] == 1
    assert hist_data["history"][0]["entry_type"] == "goods_receipt"


def test_goods_issue_webhook_simulation():
    """Verifies Goods Issue webhook posts simulated COGS deduction journal."""
    payload = {
        "sap_doc_number": "SO-DELIV-2026-901",
        "status": "GOODS_ISSUED",
        "issued_date": "2026-10-23T16:30:00Z",
        "receiver_name": "Bpk. Budi Santoso",
        "has_pod": True,
    }
    # Test via Authorization Bearer header
    res = client.post("/api/sap/goods-issue", json=payload, headers=AUTH_HEADER_BEARER)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["code"] == 200
    assert "Goods Issue and POD acknowledged" in data["message"]

    acct = data["sap_accounting_log"]
    assert acct["journal_entry"].startswith("JE-SAP-2026-")
    assert acct["posting_date"] == "2026-10-23"
    assert "501.001 - Harga Pokok Penjualan (HPP)" in acct["debit_account"]
    assert "101.001 - Persediaan Barang Jadi" in acct["credit_account"]
    assert acct["financial_status"] == "POSTED"


@patch("mock_sap_server.requests.post")
def test_trigger_master_data_success_and_error(mock_post):
    """Verifies trigger master data dispatches payload to Odoo and handles errors."""
    payload = {
        "master_type": "product",
        "data": [
            {
                "sap_material_code": "MAT-KOPI-01",
                "name": "Kopi Arabika Premium 250g",
            }
        ],
    }

    # Happy path: Odoo responds 200
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "SUCCESS", "processed_count": 1}
    mock_post.return_value = mock_resp

    res = client.post("/api/trigger/master-data", json=payload, headers=AUTH_HEADER_KEY)
    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"

    # Gateway error: Odoo host unreachable
    mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
    res_err = client.post(
        "/api/trigger/master-data", json=payload, headers=AUTH_HEADER_KEY
    )
    assert res_err.status_code == 502
    err_body = res_err.json()
    assert err_body["status"] == "ERROR"
    assert err_body["code"] == 502
    assert "Failed to connect to Odoo" in err_body["message"]


@patch("mock_sap_server.requests.post")
def test_trigger_inbound_po_success_and_error(mock_post):
    """Verifies trigger inbound PO forwards purchase orders to Odoo."""
    payload = {
        "sap_doc_number": "PO-SAP-2026-001",
        "vendor_code": "VEND-INDOMARCO",
        "expected_date": "2026-10-25",
        "items": [
            {
                "sap_material_code": "MAT-KOPI-01",
                "qty": 100.0,
                "uom": "Box",
            }
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "status": "SUCCESS",
        "code": 201,
        "odoo_picking_id": 14,
    }
    mock_post.return_value = mock_resp

    res = client.post("/api/trigger/inbound-po", json=payload, headers=AUTH_HEADER_KEY)
    assert res.status_code == 201
    assert res.json()["odoo_picking_id"] == 14

    mock_post.side_effect = requests.exceptions.Timeout("Read timeout")
    res_err = client.post(
        "/api/trigger/inbound-po", json=payload, headers=AUTH_HEADER_KEY
    )
    assert res_err.status_code == 502


@patch("mock_sap_server.requests.post")
def test_trigger_outbound_delivery_success(mock_post):
    """Verifies trigger outbound delivery forwards delivery orders to Odoo."""
    payload = {
        "sap_doc_number": "SO-DELIV-2026-901",
        "customer_code": "CUST-ALFAMART-01",
        "destination_city": "Jakarta Barat",
        "items": [
            {
                "sap_material_code": "MAT-KOPI-01",
                "qty": 50.0,
                "uom": "Box",
            }
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "SUCCESS", "code": 200, "picking_id": 25}
    mock_post.return_value = mock_resp

    res = client.post(
        "/api/trigger/outbound-delivery", json=payload, headers=AUTH_HEADER_KEY
    )
    assert res.status_code == 200
    assert res.json()["picking_id"] == 25


def test_history_inspection_and_deletion():
    """Verifies transaction history can be inspected and cleared."""
    # Post one goods receipt
    gr_payload = {
        "sap_doc_number": "PO-SAP-2026-001",
        "status": "GOODS_RECEIVED",
        "received_date": "2026-10-23T11:00:00Z",
        "warehouse_code": "WH-JKT-01",
    }
    client.post("/api/sap/goods-receipt", json=gr_payload, headers=AUTH_HEADER_KEY)

    res_get = client.get("/api/sap/history", headers=AUTH_HEADER_KEY)
    assert res_get.status_code == 200
    assert res_get.json()["count"] == 1

    # Delete history
    res_del = client.delete("/api/sap/history", headers=AUTH_HEADER_KEY)
    assert res_del.status_code == 200
    assert res_del.json()["message"] == "Transaction history cleared"

    # Confirm empty
    res_get_empty = client.get("/api/sap/history", headers=AUTH_HEADER_KEY)
    assert res_get_empty.status_code == 200
    assert res_get_empty.json()["count"] == 0


def test_accounting_generator_defaults():
    """Verifies accounting generator handles unspecified posting date gracefully."""
    acct_gr = generate_accounting_log("goods_receipt", "DOC-001")
    assert acct_gr["financial_status"] == "POSTED"
    assert "JE-SAP-" in acct_gr["journal_entry"]

    acct_gi = generate_accounting_log("goods_issue", "DOC-002")
    assert acct_gi["financial_status"] == "POSTED"
    assert "JE-SAP-" in acct_gi["journal_entry"]
