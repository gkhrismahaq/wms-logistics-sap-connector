"""SAP Upper Line Mock Service.

Provides a standalone FastAPI simulator replicating SAP Upper Line REST APIs
and webhooks for two-tier Odoo WMS integration and end-to-end testing.
"""

from __future__ import annotations

import logging
import os
import random
import threading
from datetime import datetime, timezone
from typing import Any

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Configuration & Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mock_sap_server")

DEFAULT_SAP_TOKEN = "secret_sap_token_123"
DEFAULT_ODOO_URL = os.getenv("ODOO_BASE_URL", "http://localhost:8070")
SAP_API_TOKEN = os.getenv("SAP_API_TOKEN", DEFAULT_SAP_TOKEN)

# ---------------------------------------------------------------------------
# In-Memory Transaction History Store (Thread-Safe)
# ---------------------------------------------------------------------------
_history_lock = threading.Lock()
_transaction_history: list[dict[str, Any]] = []


def record_history(
    entry_type: str,
    direction: str,
    payload: Any,
    response: Any,
    status_code: int,
) -> None:
    """Thread-safely appends a transaction log entry into memory."""
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "timestamp": now_iso,
        "entry_type": entry_type,
        "direction": direction,
        "status_code": status_code,
        "payload": payload,
        "response": response,
    }
    with _history_lock:
        _transaction_history.append(record)
    logger.info(
        "Recorded %s transaction [%s] -> %d", direction, entry_type, status_code
    )


def get_history_records() -> list[dict[str, Any]]:
    """Returns a shallow copy of all recorded transactions."""
    with _history_lock:
        return list(_transaction_history)


def clear_history_records() -> None:
    """Clears all transaction logs in memory."""
    with _history_lock:
        _transaction_history.clear()
    logger.info("Transaction history cleared.")


# ---------------------------------------------------------------------------
# SAP Accounting Journal Simulation Engine
# ---------------------------------------------------------------------------
def generate_accounting_log(
    webhook_type: str,
    sap_doc_number: str,
    posting_date: str | None = None,
) -> dict[str, Any]:
    """Generates realistic SAP General Ledger accounting journal entries."""
    if not posting_date:
        posting_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    year = posting_date.split("-")[0] if "-" in posting_date else "2026"
    suffix = random.randint(1000, 9999)
    journal_entry = f"JE-SAP-{year}-{suffix}"

    if webhook_type == "goods_receipt":
        return {
            "journal_entry": journal_entry,
            "posting_date": posting_date,
            "debit_account": "101.001 - Persediaan Barang Masuk (Rp 50.000.000)",
            "credit_account": "201.001 - Hutang Dagang Belum Difakturkan (Rp 50.000.000)",
            "vat_in_11%": "Rp 5.500.000",
            "financial_status": "POSTED",
        }

    # Goods Issue / POD default
    return {
        "journal_entry": journal_entry,
        "posting_date": posting_date,
        "debit_account": "501.001 - Harga Pokok Penjualan (HPP) (Rp 25.000.000)",
        "credit_account": "101.001 - Persediaan Barang Jadi (Rp 25.000.000)",
        "financial_status": "POSTED",
    }


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "Mock SAP Service"
    version: str = "1.0.0"


class ErrorDetail(BaseModel):
    status: str = "ERROR"
    code: int
    message: str


class SapAccountingLog(BaseModel):
    journal_entry: str = Field(..., description="SAP GL Journal Entry Document Number")
    posting_date: str = Field(..., description="Financial Posting Date (YYYY-MM-DD)")
    debit_account: str = Field(..., description="Debit GL Account and Amount")
    credit_account: str = Field(..., description="Credit GL Account and Amount")
    vat_in_11: str | None = Field(
        None, alias="vat_in_11%", description="VAT Input Value"
    )
    financial_status: str = Field("POSTED", description="Status in SAP Financials")

    model_config = {"populate_by_name": True}


class WebhookResponse(BaseModel):
    status: str = "SUCCESS"
    code: int = 200
    message: str
    sap_accounting_log: dict[str, Any]


class GoodsReceiptWebhookRequest(BaseModel):
    sap_doc_number: str = Field(..., examples=["PO-SAP-2026-001"])
    status: str = Field("GOODS_RECEIVED", examples=["GOODS_RECEIVED"])
    received_date: str = Field(..., examples=["2026-10-23T11:00:00Z"])
    warehouse_code: str = Field(..., examples=["WH-JKT-01"])


class GoodsIssueWebhookRequest(BaseModel):
    sap_doc_number: str = Field(..., examples=["SO-DELIV-2026-901"])
    status: str = Field("GOODS_ISSUED", examples=["GOODS_ISSUED"])
    issued_date: str = Field(..., examples=["2026-10-23T16:30:00Z"])
    receiver_name: str = Field(..., examples=["Bpk. Budi Santoso"])
    has_pod: bool = Field(True, examples=[True])


class MasterDataTriggerRequest(BaseModel):
    master_type: str = Field(
        ..., description="'product' or 'partner'", examples=["product"]
    )
    data: list[dict[str, Any]] = Field(
        ...,
        description="Array of material or business partner dictionaries",
        examples=[
            {
                "sap_material_code": "MAT-KOPI-01",
                "name": "Kopi Arabika Premium 250g",
                "weight": 0.25,
                "volume": 0.001,
                "barcode": "8991234567890",
            }
        ],
    )


class InboundPoItem(BaseModel):
    sap_material_code: str = Field(..., examples=["MAT-KOPI-01"])
    qty: float = Field(..., examples=[100.0])
    uom: str = Field("Box", examples=["Box"])


class InboundPoTriggerRequest(BaseModel):
    sap_doc_number: str = Field(..., examples=["PO-SAP-2026-001"])
    vendor_code: str = Field(..., examples=["VEND-INDOMARCO"])
    expected_date: str = Field(..., examples=["2026-10-25"])
    items: list[InboundPoItem] = Field(...)


class OutboundDeliveryItem(BaseModel):
    sap_material_code: str = Field(..., examples=["MAT-KOPI-01"])
    qty: float = Field(..., examples=[50.0])
    uom: str = Field("Box", examples=["Box"])


class OutboundDeliveryTriggerRequest(BaseModel):
    sap_doc_number: str = Field(..., examples=["SO-DELIV-2026-901"])
    customer_code: str = Field(..., examples=["CUST-ALFAMART-01"])
    destination_city: str = Field(..., examples=["Jakarta Barat"])
    items: list[OutboundDeliveryItem] = Field(...)


class HistoryResponse(BaseModel):
    status: str = "SUCCESS"
    count: int
    history: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Security & Authentication Dependency
# ---------------------------------------------------------------------------
def verify_sap_token(
    x_odoo_api_key: str | None = Header(None, alias="X-Odoo-API-Key"),
    authorization: str | None = Header(None, alias="Authorization"),
) -> str:
    """Validates secret token from either X-Odoo-API-Key or Authorization Bearer header.

    Raises:
        HTTPException: HTTP 401 with standard error format if invalid or missing.
    """
    token: str | None = None
    if x_odoo_api_key:
        token = x_odoo_api_key.strip()
    elif authorization:
        auth_str = authorization.strip()
        if auth_str.lower().startswith("bearer "):
            token = auth_str[7:].strip()
        else:
            token = auth_str

    expected_token = os.getenv("SAP_API_TOKEN", SAP_API_TOKEN)
    if not token or token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "ERROR",
                "code": 401,
                "message": "Unauthorized: Invalid or missing API token",
            },
        )
    return token


# ---------------------------------------------------------------------------
# FastAPI Application Definition
# ---------------------------------------------------------------------------
tags_metadata = [
    {
        "name": "General",
        "description": "Healthcheck and general service metadata endpoints.",
    },
    {
        "name": "Webhooks (Odoo -> SAP)",
        "description": "Endpoints receiving warehouse operational confirmations from Odoo.",
    },
    {
        "name": "Triggers (SAP -> Odoo)",
        "description": "Interactive endpoints to dispatch SAP master data and documents to Odoo.",
    },
    {
        "name": "Audit & History",
        "description": "Inspection and management of recorded mock transaction history.",
    },
]

app = FastAPI(
    title="SAP Upper Line Mock Service",
    description=(
        "Simulator API Two-Tier WMS & Logistics Execution System (Odoo 17 <-> SAP Upper Line).\n"
        "Menyediakan endpoint RESTful, simulasi jurnal akuntansi keuangan SAP, serta trigger otomatis."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """Ensures HTTP exceptions adhere strictly to the standardized error response contract."""
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "ERROR",
            "code": exc.status_code,
            "message": str(exc.detail),
        },
    )


# ---------------------------------------------------------------------------
# Routes: General / Healthcheck
# ---------------------------------------------------------------------------
@app.get(
    "/",
    response_model=HealthResponse,
    tags=["General"],
    summary="Root metadata endpoint",
)
def root_endpoint() -> HealthResponse:
    """Returns mock service identification and health status."""
    return HealthResponse()


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["General"],
    summary="Health check endpoint",
)
def health_endpoint() -> HealthResponse:
    """Returns status ok indicating the service is healthy."""
    return HealthResponse()


# ---------------------------------------------------------------------------
# Routes: Webhook Receivers (Odoo -> SAP)
# ---------------------------------------------------------------------------
@app.post(
    "/api/sap/goods-receipt",
    response_model=WebhookResponse,
    tags=["Webhooks (Odoo -> SAP)"],
    summary="Receive Goods Receipt confirmation from Odoo",
    responses={
        401: {"model": ErrorDetail, "description": "Unauthorized"},
    },
)
def receive_goods_receipt(
    payload: GoodsReceiptWebhookRequest,
    _token: str = Depends(verify_sap_token),
) -> WebhookResponse:
    """Receives Goods Receipt confirmation from Odoo and generates financial journal simulation."""
    posting_date = (
        payload.received_date.split("T")[0] if "T" in payload.received_date else None
    )
    acct_log = generate_accounting_log(
        webhook_type="goods_receipt",
        sap_doc_number=payload.sap_doc_number,
        posting_date=posting_date,
    )

    resp = WebhookResponse(
        status="SUCCESS",
        code=200,
        message="Goods Receipt posted into SAP General Ledger",
        sap_accounting_log=acct_log,
    )
    record_history(
        entry_type="goods_receipt",
        direction="INBOUND_WEBHOOK",
        payload=payload.model_dump(),
        response=resp.model_dump(),
        status_code=200,
    )
    return resp


@app.post(
    "/api/sap/goods-issue",
    response_model=WebhookResponse,
    tags=["Webhooks (Odoo -> SAP)"],
    summary="Receive Goods Issue / POD confirmation from Odoo",
    responses={
        401: {"model": ErrorDetail, "description": "Unauthorized"},
    },
)
def receive_goods_issue(
    payload: GoodsIssueWebhookRequest,
    _token: str = Depends(verify_sap_token),
) -> WebhookResponse:
    """Receives Goods Issue and POD confirmation from Odoo, returning financial COGS journal simulation."""
    posting_date = (
        payload.issued_date.split("T")[0] if "T" in payload.issued_date else None
    )
    acct_log = generate_accounting_log(
        webhook_type="goods_issue",
        sap_doc_number=payload.sap_doc_number,
        posting_date=posting_date,
    )

    resp = WebhookResponse(
        status="SUCCESS",
        code=200,
        message="Goods Issue and POD acknowledged in SAP Financials",
        sap_accounting_log=acct_log,
    )
    record_history(
        entry_type="goods_issue",
        direction="INBOUND_WEBHOOK",
        payload=payload.model_dump(),
        response=resp.model_dump(),
        status_code=200,
    )
    return resp


# ---------------------------------------------------------------------------
# Routes: Triggers (SAP -> Odoo)
# ---------------------------------------------------------------------------
def _dispatch_to_odoo(endpoint_path: str, payload_data: dict[str, Any]) -> JSONResponse:
    """Helper to forward HTTP POST requests to the configured Odoo instance."""
    base_url = os.getenv("ODOO_BASE_URL", DEFAULT_ODOO_URL).rstrip("/")
    target_url = f"{base_url}{endpoint_path}"
    headers = {
        "Content-Type": "application/json",
        "X-Odoo-API-Key": os.getenv("SAP_API_TOKEN", SAP_API_TOKEN),
    }

    try:
        odoo_res = requests.post(
            target_url,
            json=payload_data,
            headers=headers,
            timeout=15,
        )
        try:
            res_json = odoo_res.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            res_json = {"raw": odoo_res.text}

        record_history(
            entry_type=f"trigger:{endpoint_path}",
            direction="OUTBOUND_TRIGGER",
            payload=payload_data,
            response=res_json,
            status_code=odoo_res.status_code,
        )
        return JSONResponse(status_code=odoo_res.status_code, content=res_json)

    except requests.exceptions.RequestException as err:
        err_msg = f"Failed to connect to Odoo at {target_url}: {err}"
        logger.error(err_msg)
        err_response = {
            "status": "ERROR",
            "code": 502,
            "message": err_msg,
        }
        record_history(
            entry_type=f"trigger:{endpoint_path}",
            direction="OUTBOUND_TRIGGER",
            payload=payload_data,
            response=err_response,
            status_code=502,
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY, content=err_response
        )


@app.post(
    "/api/trigger/master-data",
    tags=["Triggers (SAP -> Odoo)"],
    summary="Trigger Master Data Sync (Product / Partner) to Odoo",
    responses={
        401: {"model": ErrorDetail, "description": "Unauthorized"},
        502: {"model": ErrorDetail, "description": "Odoo Gateway Error"},
    },
)
def trigger_master_data(
    payload: MasterDataTriggerRequest,
    _token: str = Depends(verify_sap_token),
) -> JSONResponse:
    """Dispatches product or business partner master records to Odoo /api/sap/master."""
    return _dispatch_to_odoo("/api/sap/master", payload.model_dump())


@app.post(
    "/api/trigger/inbound-po",
    tags=["Triggers (SAP -> Odoo)"],
    summary="Trigger Inbound Purchase Order to Odoo",
    responses={
        401: {"model": ErrorDetail, "description": "Unauthorized"},
        502: {"model": ErrorDetail, "description": "Odoo Gateway Error"},
    },
)
def trigger_inbound_po(
    payload: InboundPoTriggerRequest,
    _token: str = Depends(verify_sap_token),
) -> JSONResponse:
    """Dispatches Purchase Order instruction to Odoo /api/sap/inbound/po."""
    return _dispatch_to_odoo("/api/sap/inbound/po", payload.model_dump())


@app.post(
    "/api/trigger/outbound-delivery",
    tags=["Triggers (SAP -> Odoo)"],
    summary="Trigger Outbound Delivery Order to Odoo",
    responses={
        401: {"model": ErrorDetail, "description": "Unauthorized"},
        502: {"model": ErrorDetail, "description": "Odoo Gateway Error"},
    },
)
def trigger_outbound_delivery(
    payload: OutboundDeliveryTriggerRequest,
    _token: str = Depends(verify_sap_token),
) -> JSONResponse:
    """Dispatches Outbound Delivery instruction to Odoo /api/sap/outbound/delivery."""
    return _dispatch_to_odoo("/api/sap/outbound/delivery", payload.model_dump())


# ---------------------------------------------------------------------------
# Routes: History & Audit
# ---------------------------------------------------------------------------
@app.get(
    "/api/sap/history",
    response_model=HistoryResponse,
    tags=["Audit & History"],
    summary="Get in-memory transaction audit history",
    responses={
        401: {"model": ErrorDetail, "description": "Unauthorized"},
    },
)
def get_history(
    _token: str = Depends(verify_sap_token),
) -> HistoryResponse:
    """Returns list of all received webhooks and dispatched triggers."""
    records = get_history_records()
    return HistoryResponse(
        status="SUCCESS",
        count=len(records),
        history=records,
    )


@app.delete(
    "/api/sap/history",
    tags=["Audit & History"],
    summary="Clear in-memory transaction audit history",
    responses={
        401: {"model": ErrorDetail, "description": "Unauthorized"},
    },
)
def delete_history(
    _token: str = Depends(verify_sap_token),
) -> dict[str, Any]:
    """Clears in-memory transaction audit history for fresh test runs."""
    clear_history_records()
    return {
        "status": "SUCCESS",
        "code": 200,
        "message": "Transaction history cleared",
    }


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", os.getenv("MOCK_SAP_PORT", "8000")))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info("Starting SAP Upper Line Mock Service on %s:%d ...", host, port)
    uvicorn.run("mock_sap_server:app", host=host, port=port, reload=True)
