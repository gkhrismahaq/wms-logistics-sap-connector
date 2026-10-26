# -*- coding: utf-8 -*-
import base64
import json
import logging
import uuid
from datetime import datetime

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SapMasterDataController(http.Controller):
    """Controller handling incoming SAP Master Data synchronization.

    Provides authenticated, idempotent REST endpoints to upsert products
    (materials) and business partners (vendors and customers) from SAP Upper Line.
    """

    def _authenticate_request(self):
        """Validates incoming API token against wms_sap_connector.sap_api_token.

        Supports authentication via 'X-Odoo-API-Key' header or
        'Authorization: Bearer <token>' header.

        Returns:
            tuple: (is_authenticated: bool, error_response: dict or None)
        """
        configured_token = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("wms_sap_connector.sap_api_token")
        )

        auth_token = request.httprequest.headers.get("X-Odoo-API-Key")
        if not auth_token:
            auth_header = request.httprequest.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                auth_token = auth_header[7:].strip()
            elif auth_header:
                auth_token = auth_header.strip()

        if not configured_token or not auth_token or auth_token != configured_token:
            return False, {
                "status": "ERROR",
                "code": 401,
                "message": "Unauthorized: Invalid or missing API token",
            }
        return True, None

    def _generate_sync_ref(self, prefix="MD"):
        """Generates unique transaction reference: SYNC-{prefix}-YYYYMMDD-XXXXXX."""
        date_str = datetime.now().strftime("%Y%m%d")
        short_id = uuid.uuid4().hex[:6].upper()
        return f"SYNC-{prefix}-{date_str}-{short_id}"

    def _log_transaction(
        self, sync_ref, sync_type, payload_str, status, error_message=None, direction="inbound"
    ):
        """Records transaction execution in sap.sync.log using isolated sudo environment."""
        try:
            allowed_sync_types = (
                "master_product",
                "master_partner",
                "inbound_po",
                "outbound_so",
            )
            valid_sync_type = (
                sync_type
                if sync_type in allowed_sync_types
                else "master_product"
            )
            request.env["sap.sync.log"].sudo().create(
                {
                    "name": sync_ref,
                    "sync_type": valid_sync_type,
                    "direction": direction,
                    "payload": payload_str,
                    "status": status,
                    "error_message": error_message or False,
                    "sync_date": fields.Datetime.now(),
                }
            )
        except Exception as log_err:
            _logger.error("Failed to write to sap.sync.log: %s", str(log_err))

    def _process_product_master(self, data_list):
        """Processes product/material items idempotently into product.template.

        Decodes and stores Base64 images into image_1920 safely.
        """
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
                    _logger.warning("Invalid weight value for material %s", sap_material_code)

            if "volume" in item and item["volume"] is not None:
                try:
                    vals["volume"] = float(item["volume"])
                except (ValueError, TypeError):
                    _logger.warning("Invalid volume value for material %s", sap_material_code)

            if "barcode" in item and item["barcode"]:
                vals["barcode"] = str(item["barcode"]).strip()

            # Handle Base64 image
            raw_img = item.get("image_base64") or item.get("image_1920")
            if raw_img and isinstance(raw_img, str):
                clean_img = raw_img.strip()
                if "," in clean_img:
                    clean_img = clean_img.split(",", 1)[1]
                try:
                    # Validate Base64 encoding
                    base64.b64decode(clean_img, validate=True)
                    vals["image_1920"] = clean_img
                except Exception as img_err:
                    _logger.warning(
                        "Invalid Base64 image string for material %s: %s",
                        sap_material_code,
                        img_err,
                    )

            # Idempotent Upsert
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
        """Processes business partner items idempotently into res.partner.

        Classifies vendor/customer ranks based on partner_type.
        """
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

            if "street" in item and item["street"]:
                vals["street"] = str(item["street"]).strip()

            if "city" in item and item["city"]:
                vals["city"] = str(item["city"]).strip()

            if "phone" in item and item["phone"]:
                vals["phone"] = str(item["phone"]).strip()

            partner_type = str(item.get("partner_type", "")).strip().lower()
            if partner_type == "vendor":
                vals["supplier_rank"] = 1
            elif partner_type == "customer":
                vals["customer_rank"] = 1

            # Idempotent Upsert
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

    @http.route("/api/sap/master", type="http", auth="public", methods=["POST"], csrf=False)
    def receive_sap_master(self, **kwargs):
        """Public REST API endpoint to receive master data from SAP.

        Expects JSON payload with 'master_type' and 'data'.
        Validates token, processes upsert, logs to sap.sync.log, and returns standard JSON.
        """
        sync_ref = self._generate_sync_ref()

        # 1. Read Raw Payload
        payload_raw = request.httprequest.data
        payload_str = payload_raw.decode("utf-8") if payload_raw else "{}"

        # 2. Authenticate Request
        is_authenticated, auth_error = self._authenticate_request()
        if not is_authenticated:
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type="master_product",
                payload_str=payload_str,
                status="failed",
                error_message=auth_error.get("message"),
            )
            return request.make_json_response(auth_error, status=401)

        # 3. Parse JSON Body
        try:
            body = request.httprequest.get_json(silent=True)
            if not body and payload_str:
                body = json.loads(payload_str)
        except Exception:
            body = None

        if not body or not isinstance(body, dict):
            err_msg = "Bad Request: Invalid JSON body"
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type="master_product",
                payload_str=payload_str,
                status="failed",
                error_message=err_msg,
            )
            return request.make_json_response(
                {"status": "ERROR", "code": 400, "message": err_msg},
                status=400,
            )

        # Support JSON-RPC wrapped params if sent
        if "params" in body and isinstance(body["params"], dict) and "master_type" not in body:
            body = body["params"]

        master_type = body.get("master_type")
        data_list = body.get("data")

        if not master_type or not isinstance(data_list, list) or len(data_list) == 0:
            err_msg = "Bad Request: Missing 'master_type' or empty 'data' payload"
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type="master_product",
                payload_str=payload_str,
                status="failed",
                error_message=err_msg,
            )
            return request.make_json_response(
                {"status": "ERROR", "code": 400, "message": err_msg},
                status=400,
            )

        # 4. Route and Process
        sync_type = (
            "master_product"
            if master_type == "product"
            else ("master_partner" if master_type == "partner" else "master_product")
        )

        try:
            if master_type == "product":
                processed_count = self._process_product_master(data_list)
            elif master_type == "partner":
                processed_count = self._process_partner_master(data_list)
            else:
                raise ValueError(f"Bad Request: Unsupported master_type '{master_type}'")

            # 5. Success Audit Log & Response
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type=sync_type,
                payload_str=payload_str,
                status="success",
                error_message=False,
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
            _logger.exception("Error processing master data for %s: %s", sync_ref, str(exc))
            err_msg = str(exc)
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type=sync_type,
                payload_str=payload_str,
                status="failed",
                error_message=err_msg,
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

    @http.route(
        "/api/sap/inbound/po",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def receive_sap_inbound_po(self, **kwargs):
        """Public REST API endpoint to receive Purchase Orders from SAP.

        Expects JSON payload with 'sap_doc_number', 'vendor_code', and 'items'.
        Validates token, processes idempotent picking creation, logs to sap.sync.log,
        and returns standard JSON response.
        """
        sync_ref = self._generate_sync_ref(prefix="PO")

        # 1. Read Raw Payload
        payload_raw = request.httprequest.data
        payload_str = payload_raw.decode("utf-8") if payload_raw else "{}"

        # 2. Authenticate Request
        is_authenticated, auth_error = self._authenticate_request()
        if not is_authenticated:
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type="inbound_po",
                payload_str=payload_str,
                status="failed",
                error_message=auth_error.get("message"),
                direction="inbound",
            )
            return request.make_json_response(auth_error, status=401)

        # 3. Parse JSON Body
        try:
            body = request.httprequest.get_json(silent=True)
            if not body and payload_str:
                body = json.loads(payload_str, strict=False)
        except Exception:
            body = None

        if not body or not isinstance(body, dict):
            err_msg = "Bad Request: Invalid JSON body"
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type="inbound_po",
                payload_str=payload_str,
                status="failed",
                error_message=err_msg,
                direction="inbound",
            )
            return request.make_json_response(
                {"status": "ERROR", "code": 400, "message": err_msg},
                status=400,
            )

        # Support JSON-RPC params wrapping if sent
        if "params" in body and isinstance(body["params"], dict) and "sap_doc_number" not in body:
            body = body["params"]

        # 4. Validate Mandatory Payload Fields
        sap_doc_number = body.get("sap_doc_number")
        vendor_code = body.get("vendor_code")
        items = body.get("items")

        if not sap_doc_number or not isinstance(sap_doc_number, str) or not sap_doc_number.strip():
            err_msg = "Bad Request: Missing or invalid mandatory field 'sap_doc_number'"
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type="inbound_po",
                payload_str=payload_str,
                status="failed",
                error_message=err_msg,
                direction="inbound",
            )
            return request.make_json_response(
                {"status": "ERROR", "code": 400, "message": err_msg},
                status=400,
            )

        if not vendor_code or not isinstance(vendor_code, str) or not vendor_code.strip():
            err_msg = "Bad Request: Missing or invalid mandatory field 'vendor_code'"
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type="inbound_po",
                payload_str=payload_str,
                status="failed",
                error_message=err_msg,
                direction="inbound",
            )
            return request.make_json_response(
                {"status": "ERROR", "code": 400, "message": err_msg},
                status=400,
            )

        if not isinstance(items, list) or len(items) == 0:
            err_msg = "Bad Request: Missing or empty 'items' array"
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type="inbound_po",
                payload_str=payload_str,
                status="failed",
                error_message=err_msg,
                direction="inbound",
            )
            return request.make_json_response(
                {"status": "ERROR", "code": 400, "message": err_msg},
                status=400,
            )

        sap_doc_number = sap_doc_number.strip()
        vendor_code_clean = vendor_code.strip()

        # 5. Idempotent Check: Return existing picking if already created
        picking_obj = request.env["stock.picking"].sudo()
        existing_picking = picking_obj.search(
            [("sap_doc_number", "=", sap_doc_number), ("state", "!=", "cancel")],
            limit=1,
        )
        if existing_picking:
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type="inbound_po",
                payload_str=payload_str,
                status="success",
                error_message=False,
                direction="inbound",
            )
            return request.make_json_response(
                {
                    "status": "SUCCESS",
                    "code": 200,
                    "message": "Purchase order document already exists (idempotent)",
                    "odoo_picking_id": existing_picking.id,
                    "sap_doc_number": sap_doc_number,
                    "state": existing_picking.state,
                    "sync_ref": sync_ref,
                },
                status=200,
            )

        # 6. Resolve Vendor (res.partner)
        partner_obj = request.env["res.partner"].sudo()
        vendor = partner_obj.search(
            [("sap_partner_code", "=", vendor_code_clean)],
            limit=1,
        )
        if not vendor:
            err_msg = f"Bad Request: Vendor with SAP partner code '{vendor_code_clean}' not found"
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type="inbound_po",
                payload_str=payload_str,
                status="failed",
                error_message=err_msg,
                direction="inbound",
            )
            return request.make_json_response(
                {"status": "ERROR", "code": 400, "message": err_msg},
                status=400,
            )

        # 7. Resolve Operation Type (stock.picking.type) & Target Warehouse
        warehouse_code = body.get("warehouse_code") or body.get("plant_code")
        picking_type_obj = request.env["stock.picking.type"].sudo()
        warehouse_obj = request.env["stock.warehouse"].sudo()

        picking_type = None
        if warehouse_code and isinstance(warehouse_code, str):
            wh_code_clean = warehouse_code.strip()
            wh = warehouse_obj.search(
                ["|", ("code", "=", wh_code_clean), ("name", "ilike", wh_code_clean)],
                limit=1,
            )
            if wh:
                picking_type = picking_type_obj.search(
                    [("warehouse_id", "=", wh.id), ("code", "=", "incoming")],
                    limit=1,
                )

        if not picking_type:
            # Default to primary incoming picking type (DC Lowokwaru / DCLOW)
            picking_type = picking_type_obj.search(
                [("code", "=", "incoming"), ("warehouse_id.code", "=", "DCLOW")],
                limit=1,
            )
            if not picking_type:
                picking_type = picking_type_obj.search(
                    [("code", "=", "incoming")],
                    limit=1,
                )

        if not picking_type:
            err_msg = "Bad Request: Incoming operation type (stock.picking.type) not configured"
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type="inbound_po",
                payload_str=payload_str,
                status="failed",
                error_message=err_msg,
                direction="inbound",
            )
            return request.make_json_response(
                {"status": "ERROR", "code": 400, "message": err_msg},
                status=400,
            )

        # 8. Validate Material Items (product.product)
        product_obj = request.env["product.product"].sudo()
        validated_items = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                err_msg = f"Bad Request: Item #{idx + 1} must be a JSON object"
                self._log_transaction(
                    sync_ref=sync_ref,
                    sync_type="inbound_po",
                    payload_str=payload_str,
                    status="failed",
                    error_message=err_msg,
                    direction="inbound",
                )
                return request.make_json_response(
                    {"status": "ERROR", "code": 400, "message": err_msg},
                    status=400,
                )

            sap_material_code = item.get("sap_material_code")
            if not sap_material_code or not str(sap_material_code).strip():
                err_msg = f"Bad Request: Item #{idx + 1} missing mandatory field 'sap_material_code'"
                self._log_transaction(
                    sync_ref=sync_ref,
                    sync_type="inbound_po",
                    payload_str=payload_str,
                    status="failed",
                    error_message=err_msg,
                    direction="inbound",
                )
                return request.make_json_response(
                    {"status": "ERROR", "code": 400, "message": err_msg},
                    status=400,
                )

            qty = item.get("qty")
            if qty is None:
                err_msg = f"Bad Request: Item #{idx + 1} missing mandatory field 'qty'"
                self._log_transaction(
                    sync_ref=sync_ref,
                    sync_type="inbound_po",
                    payload_str=payload_str,
                    status="failed",
                    error_message=err_msg,
                    direction="inbound",
                )
                return request.make_json_response(
                    {"status": "ERROR", "code": 400, "message": err_msg},
                    status=400,
                )

            try:
                qty_val = float(qty)
                if qty_val <= 0:
                    raise ValueError("Quantity must be greater than 0")
            except (ValueError, TypeError):
                err_msg = f"Bad Request: Item #{idx + 1} ({sap_material_code}) 'qty' must be greater than 0"
                self._log_transaction(
                    sync_ref=sync_ref,
                    sync_type="inbound_po",
                    payload_str=payload_str,
                    status="failed",
                    error_message=err_msg,
                    direction="inbound",
                )
                return request.make_json_response(
                    {"status": "ERROR", "code": 400, "message": err_msg},
                    status=400,
                )

            mat_code = str(sap_material_code).strip()
            product = product_obj.search([("sap_material_code", "=", mat_code)], limit=1)
            if not product:
                err_msg = f"Bad Request: Material with SAP material code '{mat_code}' not found"
                self._log_transaction(
                    sync_ref=sync_ref,
                    sync_type="inbound_po",
                    payload_str=payload_str,
                    status="failed",
                    error_message=err_msg,
                    direction="inbound",
                )
                return request.make_json_response(
                    {"status": "ERROR", "code": 400, "message": err_msg},
                    status=400,
                )

            validated_items.append({
                "product": product,
                "qty": qty_val,
                "uom": item.get("uom"),
            })

        # 9. Parse Expected Date
        scheduled_date = fields.Datetime.now()
        expected_date_str = body.get("expected_date")
        if expected_date_str and isinstance(expected_date_str, str):
            try:
                clean_date = expected_date_str.strip().replace("Z", "")
                if "T" in clean_date:
                    scheduled_date = datetime.fromisoformat(clean_date)
                else:
                    scheduled_date = datetime.strptime(clean_date, "%Y-%m-%d")
            except Exception as dt_err:
                _logger.warning(
                    "Could not parse expected_date '%s', falling back to now(): %s",
                    expected_date_str,
                    dt_err,
                )

        # 10. Create Stock Picking and Stock Moves inside transaction
        try:
            supplier_loc = request.env.ref("stock.stock_location_suppliers", raise_if_not_found=False)
            location_id = (
                supplier_loc.id
                if supplier_loc
                else (picking_type.default_location_src_id.id or 4)
            )

            picking_vals = {
                "picking_type_id": picking_type.id,
                "partner_id": vendor.id,
                "location_id": location_id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "origin": sap_doc_number,
                "sap_doc_number": sap_doc_number,
                "sap_sync_status": "draft",
                "scheduled_date": scheduled_date,
                "company_id": picking_type.company_id.id,
            }
            picking = picking_obj.create(picking_vals)

            move_obj = request.env["stock.move"].sudo()
            for vitem in validated_items:
                prod = vitem["product"]
                move_obj.create(
                    {
                        "name": prod.display_name or prod.name,
                        "product_id": prod.id,
                        "product_uom_qty": vitem["qty"],
                        "product_uom": prod.uom_id.id,
                        "picking_id": picking.id,
                        "location_id": picking.location_id.id,
                        "location_dest_id": picking.location_dest_id.id,
                        "company_id": picking.company_id.id,
                    }
                )

            # Transition picking to 'assigned' (Ready)
            picking.action_confirm()
            if picking.state == "confirmed":
                picking.action_assign()

            # Record successful sync log
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type="inbound_po",
                payload_str=payload_str,
                status="success",
                error_message=False,
                direction="inbound",
            )

            return request.make_json_response(
                {
                    "status": "SUCCESS",
                    "code": 201,
                    "odoo_picking_id": picking.id,
                    "sap_doc_number": sap_doc_number,
                    "state": picking.state,
                    "sync_ref": sync_ref,
                },
                status=201,
            )

        except Exception as exc:
            _logger.exception("Error executing inbound PO %s: %s", sync_ref, str(exc))
            err_msg = f"Processing error: {str(exc)}"
            self._log_transaction(
                sync_ref=sync_ref,
                sync_type="inbound_po",
                payload_str=payload_str,
                status="failed",
                error_message=err_msg,
                direction="inbound",
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
