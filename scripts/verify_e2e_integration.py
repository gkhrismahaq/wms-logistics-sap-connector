"""Live End-to-End (E2E) Integration Verification Runner.

Executes live HTTP requests across running Odoo and Mock SAP containers
to validate the entire two-tier WMS integration lifecycle.
"""

from __future__ import annotations

import os
import sys
import time
import uuid

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ODOO_URL = os.getenv("ODOO_BASE_URL", "http://localhost:8070").rstrip("/")
SAP_URL = os.getenv("SAP_BASE_URL", "http://localhost:8000").rstrip("/")
SAP_TOKEN = os.getenv("SAP_API_TOKEN", "secret_sap_token_123")

DUMMY_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


def log_step(step_num: int, title: str) -> None:
    print(f"\n[{step_num}/6] >>> {title} ...")


def log_success(msg: str) -> None:
    print(f"       ✓ {msg}")


def log_failure(msg: str) -> None:
    print(f"       ✗ {msg}")


def check_preflight(session: requests.Session) -> bool:
    """Verifies that both Mock SAP and Odoo services are reachable."""
    print("=" * 70)
    print("  TWO-TIER WMS & SAP CONNECTOR — LIVE E2E INTEGRATION VERIFICATION  ")
    print("=" * 70)
    print(f"Target Odoo URL    : {ODOO_URL}")
    print(f"Target Mock SAP URL: {SAP_URL}")
    print(f"API Token          : {SAP_TOKEN[:4]}****")

    # 1. Mock SAP Healthcheck
    try:
        sap_health = session.get(f"{SAP_URL}/health", timeout=5)
        if sap_health.status_code == 200:
            log_success(f"Mock SAP Service is healthy ({sap_health.json()})")
        else:
            log_failure(f"Mock SAP returned HTTP {sap_health.status_code}")
            return False
    except requests.exceptions.RequestException as err:
        log_failure(f"Cannot reach Mock SAP at {SAP_URL}: {err}")
        return False

    # 2. Odoo Reachability
    try:
        odoo_res = session.get(f"{ODOO_URL}/web/login", timeout=10)
        if odoo_res.status_code in (200, 303, 302):
            log_success(f"Odoo 17 WMS is reachable (HTTP {odoo_res.status_code})")
        else:
            log_failure(f"Odoo returned HTTP {odoo_res.status_code}")
            return False
    except requests.exceptions.RequestException as err:
        log_failure(f"Cannot reach Odoo at {ODOO_URL}: {err}")
        return False

    return True


def test_step_1_master_data(
    session: requests.Session, unique_id: str
) -> dict[str, str]:
    """Tests master data sync (Product with Base64 image and Partners)."""
    log_step(1, "Master Data Synchronization (Product & Partners)")

    headers_api_key = {
        "Content-Type": "application/json",
        "X-Odoo-API-Key": SAP_TOKEN,
    }

    mat_code = f"MAT-E2E-{unique_id}"
    vend_code = f"VEND-E2E-{unique_id}"
    cust_code = f"CUST-E2E-{unique_id}"

    # 1. Product Master
    prod_payload = {
        "master_type": "product",
        "data": [
            {
                "sap_material_code": mat_code,
                "name": f"Kopi Spesial Gayo E2E {unique_id}",
                "weight": 0.25,
                "volume": 0.001,
                "barcode": f"899{unique_id[:8]}",
                "image_base64": DUMMY_IMAGE_BASE64,
            }
        ],
    }
    res_prod = session.post(
        f"{ODOO_URL}/api/sap/master",
        json=prod_payload,
        headers=headers_api_key,
        timeout=10,
    )
    assert res_prod.status_code == 200, f"Product sync failed: {res_prod.text}"
    prod_data = res_prod.json()
    assert prod_data.get("status") == "SUCCESS", f"Expected SUCCESS, got: {prod_data}"
    log_success(
        f"Product Material synced: {mat_code} (Processed: {prod_data.get('processed_count')})"
    )

    # 2. Partner Master (Vendor & Customer)
    headers_bearer = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SAP_TOKEN}",
    }
    partner_payload = {
        "master_type": "partner",
        "data": [
            {
                "sap_partner_code": vend_code,
                "name": f"PT Vendor Logistik {unique_id}",
                "street": "Jl. Industri No. 45",
                "city": "Bekasi",
            },
            {
                "sap_partner_code": cust_code,
                "name": f"Toko Kelontong Modern {unique_id}",
                "street": "Jl. Raya Lowokwaru No. 10",
                "city": "Malang",
            },
        ],
    }
    res_part = session.post(
        f"{ODOO_URL}/api/sap/master",
        json=partner_payload,
        headers=headers_bearer,
        timeout=10,
    )
    assert res_part.status_code == 200, f"Partner sync failed: {res_part.text}"
    log_success(f"Business Partners synced: Vendor {vend_code}, Customer {cust_code}")

    return {
        "mat_code": mat_code,
        "vend_code": vend_code,
        "cust_code": cust_code,
    }


def test_step_2_inbound_po(
    session: requests.Session,
    unique_id: str,
    master_info: dict[str, str],
) -> str:
    """Tests Inbound Purchase Order creation in Odoo."""
    log_step(2, "Inbound Purchase Order (SAP -> Odoo)")

    sap_po_num = f"PO-SAP-E2E-{unique_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Odoo-API-Key": SAP_TOKEN,
    }
    payload = {
        "sap_doc_number": sap_po_num,
        "vendor_code": master_info["vend_code"],
        "expected_date": "2026-10-30",
        "items": [
            {
                "sap_material_code": master_info["mat_code"],
                "qty": 150.0,
                "uom": "Box",
            }
        ],
    }

    res = session.post(
        f"{ODOO_URL}/api/sap/inbound/po",
        json=payload,
        headers=headers,
        timeout=10,
    )
    assert res.status_code == 201, f"PO creation failed ({res.status_code}): {res.text}"
    data = res.json()
    assert data.get("status") == "SUCCESS", f"Expected SUCCESS, got: {data}"
    picking_id = data.get("odoo_picking_id")
    log_success(
        f"Stock Receipt generated: Picking ID #{picking_id} for SAP Doc {sap_po_num}"
    )
    return sap_po_num


def test_step_3_goods_receipt_webhook(
    session: requests.Session,
    sap_po_num: str,
) -> None:
    """Tests Goods Receipt webhook reception on Mock SAP and accounting simulation."""
    log_step(3, "Goods Receipt Webhook Confirmation (Odoo -> SAP)")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SAP_TOKEN}",
    }
    payload = {
        "sap_doc_number": sap_po_num,
        "status": "GOODS_RECEIVED",
        "received_date": "2026-10-27T10:00:00Z",
        "warehouse_code": "WH-E2E-01",
    }

    res = session.post(
        f"{SAP_URL}/api/sap/goods-receipt",
        json=payload,
        headers=headers,
        timeout=5,
    )
    assert res.status_code == 200, f"Goods Receipt webhook failed: {res.text}"
    data = res.json()
    assert data.get("status") == "SUCCESS"
    acct = data.get("sap_accounting_log", {})
    assert "JE-SAP-" in acct.get("journal_entry", "")
    assert acct.get("financial_status") == "POSTED"
    log_success(
        f"Goods Receipt confirmed in SAP GL: {acct.get('journal_entry')} "
        f"({acct.get('debit_account')[:28]}...)"
    )


def test_step_4_outbound_delivery(
    session: requests.Session,
    unique_id: str,
    master_info: dict[str, str],
) -> str:
    """Tests Outbound Delivery creation in Odoo."""
    log_step(4, "Outbound Delivery Order (SAP -> Odoo)")

    sap_so_num = f"SO-DELIV-E2E-{unique_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Odoo-API-Key": SAP_TOKEN,
    }
    payload = {
        "sap_doc_number": sap_so_num,
        "customer_code": master_info["cust_code"],
        "destination_city": "Malang",
        "items": [
            {
                "sap_material_code": master_info["mat_code"],
                "qty": 50.0,
                "uom": "Box",
            }
        ],
    }

    res = session.post(
        f"{ODOO_URL}/api/sap/outbound/delivery",
        json=payload,
        headers=headers,
        timeout=10,
    )
    assert res.status_code == 200, f"Outbound delivery creation failed: {res.text}"
    data = res.json()
    assert data.get("status") == "SUCCESS"
    picking_name = data.get("picking_name")
    log_success(f"Delivery Order generated: {picking_name} for SAP Doc {sap_so_num}")
    return sap_so_num


def test_step_5_goods_issue_webhook(
    session: requests.Session,
    sap_so_num: str,
) -> None:
    """Tests Goods Issue & POD webhook reception on Mock SAP."""
    log_step(5, "Goods Issue & POD Webhook Confirmation (Odoo -> SAP)")

    headers = {
        "Content-Type": "application/json",
        "X-Odoo-API-Key": SAP_TOKEN,
    }
    payload = {
        "sap_doc_number": sap_so_num,
        "status": "GOODS_ISSUED",
        "issued_date": "2026-10-27T15:30:00Z",
        "receiver_name": "Bpk. Bambang Sutrisno",
        "has_pod": True,
    }

    res = session.post(
        f"{SAP_URL}/api/sap/goods-issue",
        json=payload,
        headers=headers,
        timeout=5,
    )
    assert res.status_code == 200, f"Goods Issue webhook failed: {res.text}"
    data = res.json()
    assert data.get("status") == "SUCCESS"
    acct = data.get("sap_accounting_log", {})
    assert "JE-SAP-" in acct.get("journal_entry", "")
    assert acct.get("financial_status") == "POSTED"
    log_success(
        f"Goods Issue confirmed in SAP Financials: {acct.get('journal_entry')} "
        f"({acct.get('debit_account')[:28]}...)"
    )


def test_step_6_mock_sap_audit_history(session: requests.Session) -> None:
    """Verifies all E2E transactions are safely captured in Mock SAP audit history."""
    log_step(6, "Audit History Verification on Mock SAP")

    headers = {"X-Odoo-API-Key": SAP_TOKEN}
    res = session.get(f"{SAP_URL}/api/sap/history", headers=headers, timeout=5)
    assert res.status_code == 200, f"Failed to get history: {res.text}"
    data = res.json()
    assert data.get("status") == "SUCCESS"
    count = data.get("count", 0)
    assert count >= 2, f"Expected at least 2 recorded transactions, got {count}"
    log_success(
        f"Audit log verified: {count} transactions successfully logged in Mock SAP"
    )


def main() -> int:
    """Main CLI execution flow."""
    session = requests.Session()
    if not check_preflight(session):
        print("\n[ERROR] Pre-flight healthcheck failed. Aborting E2E validation.")
        return 1

    unique_id = f"{int(time.time())}-{uuid.uuid4().hex[:4].upper()}"
    start_time = time.time()

    try:
        master_info = test_step_1_master_data(session, unique_id)
        sap_po_num = test_step_2_inbound_po(session, unique_id, master_info)
        test_step_3_goods_receipt_webhook(session, sap_po_num)
        sap_so_num = test_step_4_outbound_delivery(session, unique_id, master_info)
        test_step_5_goods_issue_webhook(session, sap_so_num)
        test_step_6_mock_sap_audit_history(session)

        elapsed = time.time() - start_time
        print("\n" + "=" * 70)
        print(f"  ALL 6 E2E INTEGRATION TESTS PASSED SUCCESSFULLY! ({elapsed:.2f}s)  ")
        print("=" * 70 + "\n")
        return 0

    except AssertionError as err:
        print(f"\n[E2E ASSERTION ERROR] {err}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\n[UNEXPECTED ERROR] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
