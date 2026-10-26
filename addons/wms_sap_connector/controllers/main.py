import base64
import json
import logging
import uuid
from datetime import datetime

from odoo import fields, http
from odoo.http import request

from ..constants import (
    ALLOWED_SYNC_TYPES,
    AUTH_BEARER_PREFIX,
    CONFIG_PARAM_SAP_API_TOKEN,
    DIRECTION_INBOUND,
    ERROR_INVALID_JSON,
    ERROR_UNAUTHORIZED,
    HTTP_HEADER_API_KEY,
    HTTP_HEADER_AUTHORIZATION,
    MASTER_TYPE_PARTNER,
    MASTER_TYPE_PRODUCT,
    PARTNER_TYPE_CUSTOMER,
    PARTNER_TYPE_VENDOR,
    REF_PREFIX_INBOUND_PO,
    REF_PREFIX_MASTER_DATA,
    SYNC_STATUS_FAILED,
    SYNC_STATUS_SUCCESS,
    SYNC_TYPE_INBOUND_PO,
    SYNC_TYPE_MASTER_PARTNER,
    SYNC_TYPE_MASTER_PRODUCT,
)

_logger = logging.getLogger(__name__)


class SapBaseController(http.Controller):
    """Base controller providing common authentication, reference generation, and logging."""

    def _authenticate_request(self):
        """Validates incoming API token against configured system parameter."""
        configured_token = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param(CONFIG_PARAM_SAP_API_TOKEN)
        )

        auth_token = request.httprequest.headers.get(HTTP_HEADER_API_KEY)
        if not auth_token:
            auth_header = request.httprequest.headers.get(HTTP_HEADER_AUTHORIZATION, "")
            if auth_header.startswith(AUTH_BEARER_PREFIX):
                auth_token = auth_header[len(AUTH_BEARER_PREFIX) :].strip()
            elif auth_header:
                auth_token = auth_header.strip()

        if not configured_token or not auth_token or auth_token != configured_token:
            return False, {
                "status": "ERROR",
                "code": 401,
                "message": ERROR_UNAUTHORIZED,
            }
        return True, None

    def _generate_sync_ref(self, prefix=REF_PREFIX_MASTER_DATA):
        """Generates unique transaction reference: SYNC-{prefix}-YYYYMMDD-XXXXXX."""
        date_str = datetime.now().strftime("%Y%m%d")
        short_id = uuid.uuid4().hex[:6].upper()
        return f"SYNC-{prefix}-{date_str}-{short_id}"

    def _log_transaction(
        self,
        sync_ref,
        sync_type,
        payload_str,
        status,
        error_message=None,
        direction=DIRECTION_INBOUND,
    ):
        """Records transaction execution in sap.sync.log using isolated sudo environment."""
        if sync_type not in ALLOWED_SYNC_TYPES:
            raise ValueError(
                f"Invalid sync_type '{sync_type}'. Must be one of {ALLOWED_SYNC_TYPES}"
            )

        try:
            request.env["sap.sync.log"].sudo().create(
                {
                    "name": sync_ref,
                    "sync_type": sync_type,
                    "direction": direction,
                    "payload": payload_str,
                    "status": status,
                    "error_message": error_message or False,
                    "sync_date": fields.Datetime.now(),
                }
            )
        except Exception as log_err:
            _logger.error(
                "Failed to write to sap.sync.log for %s: %s", sync_ref, str(log_err)
            )

    def _extract_and_authenticate_payload(self, prefix, sync_type):
        """Extracts, authenticates, and parses incoming JSON payload.

        Returns:
            tuple: (sync_ref, payload_str, body, error_response)
        """
        sync_ref = self._generate_sync_ref(prefix=prefix)
        payload_raw = request.httprequest.data
        payload_str = payload_raw.decode("utf-8") if payload_raw else "{}"

        is_authenticated, auth_error = self._authenticate_request()
        if not is_authenticated:
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type=sync_type,
                payload_str=payload_str,
                status=SYNC_STATUS_FAILED,
                error_message=auth_error.get("message"),
                direction=DIRECTION_INBOUND,
            )
            return (
                sync_ref,
                payload_str,
                None,
                request.make_json_response(auth_error, status=401),
            )

        try:
            body = request.httprequest.get_json(silent=True)
            if not body and payload_str:
                body = json.loads(payload_str, strict=False)
        except Exception:
            body = None

        if not body or not isinstance(body, dict):
            err_msg = ERROR_INVALID_JSON
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type=sync_type,
                payload_str=payload_str,
                status=SYNC_STATUS_FAILED,
                error_message=err_msg,
                direction=DIRECTION_INBOUND,
            )
            return (
                sync_ref,
                payload_str,
                None,
                request.make_json_response(
                    {"status": "ERROR", "code": 400, "message": err_msg},
                    status=400,
                ),
            )

        if "params" in body and isinstance(body["params"], dict):
            if "master_type" in body["params"] or "sap_doc_number" in body["params"]:
                body = body["params"]

        return sync_ref, payload_str, body, None


class SapMasterDataController(SapBaseController):
    """Controller handling incoming SAP Master Data synchronization."""

    def _process_product_master(self, data_list):
        """Processes product/material items idempotently into product.template."""
        product_tmpl_obj = request.env["product.template"].sudo()
        processed_count = 0

        for item in data_list:
            if not isinstance(item, dict):
                raise ValueError("Item in product data list must be a JSON object.")

            sap_material_code = item.get("sap_material_code")
            name = item.get("name")

            if not sap_material_code or not name:
                raise ValueError(
                    "Missing mandatory field 'sap_material_code' or 'name' in product item."
                )

            vals = {
                "name": str(name).strip(),
            }

            if "weight" in item and item["weight"] is not None:
                try:
                    vals["weight"] = float(item["weight"])
                except (ValueError, TypeError):
                    _logger.warning(
                        "Invalid weight value for material %s", sap_material_code
                    )

            if "volume" in item and item["volume"] is not None:
                try:
                    vals["volume"] = float(item["volume"])
                except (ValueError, TypeError):
                    _logger.warning(
                        "Invalid volume value for material %s", sap_material_code
                    )

            if item.get("barcode"):
                vals["barcode"] = str(item["barcode"]).strip()

            raw_img = item.get("image_base64") or item.get("image_1920")
            if raw_img and isinstance(raw_img, str):
                clean_img = raw_img.strip()
                if "," in clean_img:
                    clean_img = clean_img.split(",", 1)[1]
                try:
                    base64.b64decode(clean_img, validate=True)
                    vals["image_1920"] = clean_img
                except Exception as img_err:
                    _logger.warning(
                        "Invalid Base64 image string for material %s: %s",
                        sap_material_code,
                        img_err,
                    )

            existing_product = product_tmpl_obj.search(
                [("sap_material_code", "=", sap_material_code)], limit=1
            )
            if existing_product:
                existing_product.write(vals)
            else:
                vals["sap_material_code"] = sap_material_code
                vals["type"] = "product"
                product_tmpl_obj.create(vals)

            processed_count += 1

        return processed_count

    def _process_partner_master(self, data_list):
        """Processes business partner items idempotently into res.partner."""
        partner_obj = request.env["res.partner"].sudo()
        processed_count = 0

        for item in data_list:
            if not isinstance(item, dict):
                raise ValueError("Item in partner data list must be a JSON object.")

            sap_partner_code = item.get("sap_partner_code")
            name = item.get("name")

            if not sap_partner_code or not name:
                raise ValueError(
                    "Missing mandatory field 'sap_partner_code' or 'name' in partner item."
                )

            vals = {
                "name": str(name).strip(),
            }

            if item.get("street"):
                vals["street"] = str(item["street"]).strip()

            if item.get("city"):
                vals["city"] = str(item["city"]).strip()

            if item.get("phone"):
                vals["phone"] = str(item["phone"]).strip()

            partner_type = str(item.get("partner_type", "")).strip().lower()
            if partner_type == PARTNER_TYPE_VENDOR:
                vals["supplier_rank"] = 1
            elif partner_type == PARTNER_TYPE_CUSTOMER:
                vals["customer_rank"] = 1

            existing_partner = partner_obj.search(
                [("sap_partner_code", "=", sap_partner_code)], limit=1
            )
            if existing_partner:
                existing_partner.write(vals)
            else:
                vals["sap_partner_code"] = sap_partner_code
                partner_obj.create(vals)

            processed_count += 1

        return processed_count

    @http.route(
        "/api/sap/master", type="http", auth="public", methods=["POST"], csrf=False
    )
    def receive_sap_master(self, **kwargs):
        """Public REST API endpoint to receive master data from SAP."""
        sync_ref, payload_str, body, error_response = (
            self._extract_and_authenticate_payload(
                prefix=REF_PREFIX_MASTER_DATA,
                sync_type=SYNC_TYPE_MASTER_PRODUCT,
            )
        )
        if error_response:
            return error_response

        master_type = body.get("master_type")
        data_list = body.get("data")

        if not master_type or not isinstance(data_list, list) or len(data_list) == 0:
            err_msg = "Bad Request: Missing 'master_type' or empty 'data' payload"
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type=SYNC_TYPE_MASTER_PRODUCT,
                payload_str=payload_str,
                status=SYNC_STATUS_FAILED,
                error_message=err_msg,
                direction=DIRECTION_INBOUND,
            )
            return request.make_json_response(
                {"status": "ERROR", "code": 400, "message": err_msg},
                status=400,
            )

        sync_type = (
            SYNC_TYPE_MASTER_PRODUCT
            if master_type == MASTER_TYPE_PRODUCT
            else (
                SYNC_TYPE_MASTER_PARTNER
                if master_type == MASTER_TYPE_PARTNER
                else SYNC_TYPE_MASTER_PRODUCT
            )
        )

        try:
            if master_type == MASTER_TYPE_PRODUCT:
                processed_count = self._process_product_master(data_list)
            elif master_type == MASTER_TYPE_PARTNER:
                processed_count = self._process_partner_master(data_list)
            else:
                raise ValueError(
                    f"Bad Request: Unsupported master_type '{master_type}'"
                )

            self._log_transaction(
                sync_ref=sync_ref,
                sync_type=sync_type,
                payload_str=payload_str,
                status=SYNC_STATUS_SUCCESS,
                error_message=False,
                direction=DIRECTION_INBOUND,
            )
            return request.make_json_response(
                {
                    "status": "SUCCESS",
                    "code": 200,
                    "message": "Master data processed successfully",
                    "sync_ref": sync_ref,
                    "processed_count": processed_count,
                },
                status=200,
            )

        except Exception as exc:
            request.env.cr.rollback()
            _logger.exception(
                "Error processing master data for %s: %s", sync_ref, str(exc)
            )
            err_msg = str(exc)
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type=sync_type,
                payload_str=payload_str,
                status=SYNC_STATUS_FAILED,
                error_message=err_msg,
                direction=DIRECTION_INBOUND,
            )
            return request.make_json_response(
                {
                    "status": "ERROR",
                    "code": 400,
                    "message": f"Processing error: {err_msg}",
                    "sync_ref": sync_ref,
                },
                status=400,
            )


class SapInboundController(SapBaseController):
    """Controller handling incoming SAP Purchase Orders."""

    @http.route(
        "/api/sap/inbound/po",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def receive_sap_inbound_po(self, **kwargs):
        """Public REST API endpoint to receive Purchase Orders from SAP."""
        sync_ref, payload_str, body, error_response = (
            self._extract_and_authenticate_payload(
                prefix=REF_PREFIX_INBOUND_PO,
                sync_type=SYNC_TYPE_INBOUND_PO,
            )
        )
        if error_response:
            return error_response

        try:
            picking, is_created = (
                request.env["stock.picking"].sudo().create_inbound_from_sap(body)
            )
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type=SYNC_TYPE_INBOUND_PO,
                payload_str=payload_str,
                status=SYNC_STATUS_SUCCESS,
                error_message=False,
                direction=DIRECTION_INBOUND,
            )
            if is_created:
                return request.make_json_response(
                    {
                        "status": "SUCCESS",
                        "code": 201,
                        "odoo_picking_id": picking.id,
                        "sap_doc_number": picking.sap_doc_number,
                        "state": picking.state,
                        "sync_ref": sync_ref,
                    },
                    status=201,
                )
            else:
                return request.make_json_response(
                    {
                        "status": "SUCCESS",
                        "code": 200,
                        "message": "Purchase order document already exists (idempotent)",
                        "odoo_picking_id": picking.id,
                        "sap_doc_number": picking.sap_doc_number,
                        "state": picking.state,
                        "sync_ref": sync_ref,
                    },
                    status=200,
                )
        except Exception as exc:
            request.env.cr.rollback()
            _logger.exception("Failed to process inbound PO %s: %s", sync_ref, str(exc))
            err_msg = str(exc)
            if not err_msg.startswith("Bad Request:"):
                err_msg = f"Processing error: {err_msg}"
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type=SYNC_TYPE_INBOUND_PO,
                payload_str=payload_str,
                status=SYNC_STATUS_FAILED,
                error_message=err_msg,
                direction=DIRECTION_INBOUND,
            )
            return request.make_json_response(
                {
                    "status": "ERROR",
                    "code": 400,
                    "message": err_msg,
                    "sync_ref": sync_ref,
                },
                status=400,
            )
