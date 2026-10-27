"""Webhook client service for transmitting outbound SAP events."""

import json
import logging

import requests
from odoo import fields

from ..constants import (
    AUTH_BEARER_PREFIX,
    CONFIG_PARAM_SAP_API_TOKEN,
    CONFIG_PARAM_SAP_BASE_URL,
    DATE_FMT_ISO_UTC,
    DEFAULT_RECEIVER_NAME,
    DIRECTION_OUTBOUND,
    ERR_SAP_BASE_URL_NOT_SET,
    HTTP_HEADER_API_KEY,
    HTTP_HEADER_AUTHORIZATION,
    HTTP_HEADER_CONTENT_TYPE,
    HTTP_MIME_JSON,
    HTTP_STATUS_CREATED,
    HTTP_STATUS_OK,
    REF_PREFIX_GOODS_ISSUE,
    REF_PREFIX_GOODS_RECEIPT,
    SAP_ENDPOINT_GOODS_ISSUE,
    SAP_ENDPOINT_GOODS_RECEIPT,
    SYNC_STATUS_FAILED,
    SYNC_STATUS_SUCCESS,
    SYNC_STATUS_SYNCED,
    SYNC_TYPE_INBOUND_PO,
    SYNC_TYPE_OUTBOUND_SO,
    WEBHOOK_STATUS_GOODS_ISSUED,
    WEBHOOK_STATUS_GOODS_RECEIVED,
    WEBHOOK_TIMEOUT_SECONDS,
)

_logger = logging.getLogger(__name__)


def send_goods_receipt_webhook(picking):
    """Sends Goods Receipt confirmation webhook HTTP POST to SAP Upper Line."""
    if not picking.sap_doc_number:
        return

    sync_ref = picking.env["sap.sync.log"].generate_sync_ref(REF_PREFIX_GOODS_RECEIPT)
    sap_base_url = (
        picking.env["ir.config_parameter"].sudo().get_param(CONFIG_PARAM_SAP_BASE_URL)
    )
    sap_api_token = (
        picking.env["ir.config_parameter"].sudo().get_param(CONFIG_PARAM_SAP_API_TOKEN)
    )

    received_date = (picking.date_done or fields.Datetime.now()).strftime(
        DATE_FMT_ISO_UTC
    )
    warehouse_code = picking.picking_type_id.warehouse_id.code or (
        picking.location_dest_id.warehouse_id.code
        if picking.location_dest_id.warehouse_id
        else "WH"
    )

    payload = {
        "sap_doc_number": picking.sap_doc_number,
        "status": WEBHOOK_STATUS_GOODS_RECEIVED,
        "received_date": received_date,
        "warehouse_code": warehouse_code,
    }
    payload_str = json.dumps(payload)

    if not sap_base_url:
        _logger.warning(
            "Picking %s Goods Receipt webhook aborted: %s",
            picking.name,
            ERR_SAP_BASE_URL_NOT_SET,
        )
        picking.sudo().write({"sap_sync_status": SYNC_STATUS_FAILED})
        picking.env["sap.sync.log"].sudo().create(
            {
                "name": sync_ref,
                "sync_type": SYNC_TYPE_INBOUND_PO,
                "direction": DIRECTION_OUTBOUND,
                "payload": payload_str,
                "response_payload": False,
                "status": SYNC_STATUS_FAILED,
                "error_message": ERR_SAP_BASE_URL_NOT_SET,
                "sync_date": fields.Datetime.now(),
            }
        )
        return

    endpoint_url = sap_base_url.rstrip("/") + SAP_ENDPOINT_GOODS_RECEIPT
    headers = {
        HTTP_HEADER_CONTENT_TYPE: HTTP_MIME_JSON,
    }
    if sap_api_token:
        headers[HTTP_HEADER_AUTHORIZATION] = f"{AUTH_BEARER_PREFIX}{sap_api_token}"
        headers[HTTP_HEADER_API_KEY] = sap_api_token

    try:
        response = requests.post(
            endpoint_url,
            data=payload_str,
            headers=headers,
            timeout=WEBHOOK_TIMEOUT_SECONDS,
        )
        resp_text = response.text
        if response.status_code in (HTTP_STATUS_OK, HTTP_STATUS_CREATED):
            _logger.info(
                "Goods Receipt webhook success for %s: %s",
                picking.sap_doc_number,
                resp_text,
            )
            picking.sudo().write({"sap_sync_status": SYNC_STATUS_SYNCED})
            picking.env["sap.sync.log"].sudo().create(
                {
                    "name": sync_ref,
                    "sync_type": SYNC_TYPE_INBOUND_PO,
                    "direction": DIRECTION_OUTBOUND,
                    "payload": payload_str,
                    "response_payload": resp_text,
                    "status": SYNC_STATUS_SUCCESS,
                    "error_message": False,
                    "sync_date": fields.Datetime.now(),
                }
            )
        else:
            err_msg = f"SAP responded with HTTP {response.status_code}: {resp_text}"
            _logger.error(
                "Goods Receipt webhook failed for %s: %s",
                picking.sap_doc_number,
                err_msg,
            )
            picking.sudo().write({"sap_sync_status": SYNC_STATUS_FAILED})
            picking.env["sap.sync.log"].sudo().create(
                {
                    "name": sync_ref,
                    "sync_type": SYNC_TYPE_INBOUND_PO,
                    "direction": DIRECTION_OUTBOUND,
                    "payload": payload_str,
                    "response_payload": resp_text,
                    "status": SYNC_STATUS_FAILED,
                    "error_message": err_msg,
                    "sync_date": fields.Datetime.now(),
                }
            )
    except Exception as exc:
        err_msg = f"Connection error: {exc!s}"
        _logger.exception(
            "Failed to send Goods Receipt webhook for %s",
            picking.sap_doc_number,
        )
        picking.sudo().write({"sap_sync_status": SYNC_STATUS_FAILED})
        picking.env["sap.sync.log"].sudo().create(
            {
                "name": sync_ref,
                "sync_type": SYNC_TYPE_INBOUND_PO,
                "direction": DIRECTION_OUTBOUND,
                "payload": payload_str,
                "response_payload": False,
                "status": SYNC_STATUS_FAILED,
                "error_message": err_msg,
                "sync_date": fields.Datetime.now(),
            }
        )


def send_goods_issue_webhook(picking):
    """Sends Goods Issue & POD confirmation webhook HTTP POST to SAP Upper Line."""
    if not picking.sap_doc_number or not picking.has_pod:
        return

    sync_ref = picking.env["sap.sync.log"].generate_sync_ref(REF_PREFIX_GOODS_ISSUE)
    sap_base_url = (
        picking.env["ir.config_parameter"].sudo().get_param(CONFIG_PARAM_SAP_BASE_URL)
    )
    sap_api_token = (
        picking.env["ir.config_parameter"].sudo().get_param(CONFIG_PARAM_SAP_API_TOKEN)
    )

    issued_date = (
        picking.pod_timestamp or picking.date_done or fields.Datetime.now()
    ).strftime(DATE_FMT_ISO_UTC)

    payload = {
        "sap_doc_number": picking.sap_doc_number,
        "status": WEBHOOK_STATUS_GOODS_ISSUED,
        "issued_date": issued_date,
        "receiver_name": picking.pod_signed_by or DEFAULT_RECEIVER_NAME,
        "has_pod": bool(picking.has_pod),
    }
    payload_str = json.dumps(payload)

    if not sap_base_url:
        _logger.warning(
            "Picking %s Goods Issue webhook aborted: %s",
            picking.name,
            ERR_SAP_BASE_URL_NOT_SET,
        )
        picking.sudo().write({"sap_sync_status": SYNC_STATUS_FAILED})
        picking.env["sap.sync.log"].sudo().create(
            {
                "name": sync_ref,
                "sync_type": SYNC_TYPE_OUTBOUND_SO,
                "direction": DIRECTION_OUTBOUND,
                "payload": payload_str,
                "response_payload": False,
                "status": SYNC_STATUS_FAILED,
                "error_message": ERR_SAP_BASE_URL_NOT_SET,
                "sync_date": fields.Datetime.now(),
            }
        )
        return

    endpoint_url = sap_base_url.rstrip("/") + SAP_ENDPOINT_GOODS_ISSUE
    headers = {
        HTTP_HEADER_CONTENT_TYPE: HTTP_MIME_JSON,
    }
    if sap_api_token:
        headers[HTTP_HEADER_AUTHORIZATION] = f"{AUTH_BEARER_PREFIX}{sap_api_token}"
        headers[HTTP_HEADER_API_KEY] = sap_api_token

    try:
        response = requests.post(
            endpoint_url,
            data=payload_str,
            headers=headers,
            timeout=WEBHOOK_TIMEOUT_SECONDS,
        )
        resp_text = response.text
        if response.status_code in (HTTP_STATUS_OK, HTTP_STATUS_CREATED):
            _logger.info(
                "Goods Issue webhook success for %s: %s",
                picking.sap_doc_number,
                resp_text,
            )
            picking.sudo().write({"sap_sync_status": SYNC_STATUS_SYNCED})
            picking.env["sap.sync.log"].sudo().create(
                {
                    "name": sync_ref,
                    "sync_type": SYNC_TYPE_OUTBOUND_SO,
                    "direction": DIRECTION_OUTBOUND,
                    "payload": payload_str,
                    "response_payload": resp_text,
                    "status": SYNC_STATUS_SUCCESS,
                    "error_message": False,
                    "sync_date": fields.Datetime.now(),
                }
            )
        else:
            err_msg = f"SAP responded with HTTP {response.status_code}: {resp_text}"
            _logger.error(
                "Goods Issue webhook failed for %s: %s",
                picking.sap_doc_number,
                err_msg,
            )
            picking.sudo().write({"sap_sync_status": SYNC_STATUS_FAILED})
            picking.env["sap.sync.log"].sudo().create(
                {
                    "name": sync_ref,
                    "sync_type": SYNC_TYPE_OUTBOUND_SO,
                    "direction": DIRECTION_OUTBOUND,
                    "payload": payload_str,
                    "response_payload": resp_text,
                    "status": SYNC_STATUS_FAILED,
                    "error_message": err_msg,
                    "sync_date": fields.Datetime.now(),
                }
            )
    except Exception as exc:
        err_msg = f"Connection error: {exc!s}"
        _logger.exception(
            "Failed to send Goods Issue webhook for %s",
            picking.sap_doc_number,
        )
        picking.sudo().write({"sap_sync_status": SYNC_STATUS_FAILED})
        picking.env["sap.sync.log"].sudo().create(
            {
                "name": sync_ref,
                "sync_type": SYNC_TYPE_OUTBOUND_SO,
                "direction": DIRECTION_OUTBOUND,
                "payload": payload_str,
                "response_payload": False,
                "status": SYNC_STATUS_FAILED,
                "error_message": err_msg,
                "sync_date": fields.Datetime.now(),
            }
        )
