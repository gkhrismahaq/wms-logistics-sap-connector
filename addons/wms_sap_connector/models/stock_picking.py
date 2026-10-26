import json
import logging
import uuid
from datetime import datetime, time, timezone

import requests
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..constants import (
    AUTH_BEARER_PREFIX,
    CONFIG_PARAM_SAP_API_TOKEN,
    CONFIG_PARAM_SAP_BASE_URL,
    DIRECTION_OUTBOUND,
    HTTP_HEADER_API_KEY,
    HTTP_HEADER_AUTHORIZATION,
    PICKING_STATE_CANCEL,
    PICKING_STATE_CONFIRMED,
    PICKING_TYPE_CODE_INCOMING,
    PICKING_TYPE_CODE_OUTGOING,
    REF_PREFIX_GOODS_RECEIPT,
    SAP_ENDPOINT_GOODS_RECEIPT,
    SAP_PICKING_SYNC_STATUS_SELECTION,
    SYNC_STATUS_DRAFT,
    SYNC_STATUS_FAILED,
    SYNC_STATUS_SUCCESS,
    SYNC_STATUS_SYNCED,
    SYNC_TYPE_INBOUND_PO,
    WEBHOOK_STATUS_GOODS_RECEIVED,
    WEBHOOK_TIMEOUT_SECONDS,
)

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    sap_doc_number = fields.Char(
        string="SAP Document Number",
        index=True,
        copy=False,
        help="Original SAP purchase order or delivery document reference (e.g. PO-SAP-2026-001).",
    )
    sap_sync_status = fields.Selection(
        selection=SAP_PICKING_SYNC_STATUS_SELECTION,
        string="SAP Sync Status",
        default=SYNC_STATUS_DRAFT,
        index=True,
        copy=False,
        help="Lifecycle status of document synchronization with SAP.",
    )
    vehicle_id = fields.Many2one(
        comodel_name="wms.vehicle",
        string="Vehicle / Fleet",
        domain="[('state', '!=', 'maintenance')]",
        index=True,
        copy=False,
        help="Physical cargo delivery vehicle assigned to this transfer.",
    )
    driver_id = fields.Many2one(
        comodel_name="res.partner",
        string="Driver",
        domain="[('is_company', '=', False)]",
        copy=False,
        help="Responsible courier or driver conducting the delivery.",
    )
    total_weight = fields.Float(
        string="Total Weight (kg)",
        compute="_compute_total_weight_volume",
        store=True,
        digits=(12, 2),
        help="Aggregated total weight in kilograms computed from all active stock moves.",
    )
    total_volume = fields.Float(
        string="Total Volume (m³)",
        compute="_compute_total_weight_volume",
        store=True,
        digits=(12, 4),
        help="Aggregated total volume in cubic meters computed from all active stock moves.",
    )
    proof_of_delivery = fields.Binary(
        string="Proof of Delivery (Image / Signature)",
        attachment=True,
        copy=False,
        help="Photo proof of physical handover or scanned signature at destination.",
    )
    pod_signed_by = fields.Char(
        string="Received / Signed By",
        copy=False,
        help="Full name of store receiver or authorized person receiving the cargo.",
    )
    pod_timestamp = fields.Datetime(
        string="POD Timestamp",
        copy=False,
        help="Timestamp when proof of delivery was recorded.",
    )
    has_pod = fields.Boolean(
        string="Has POD",
        compute="_compute_has_pod",
        store=True,
        index=True,
        help="Indicates whether physical proof of delivery is available.",
    )

    _sql_constraints = [
        (
            "sap_doc_number_uniq",
            "unique(sap_doc_number)",
            "The SAP document number must be unique across all transfer documents.",
        ),
    ]

    @api.depends("proof_of_delivery", "pod_signed_by")
    def _compute_has_pod(self):
        """Computes whether physical proof of delivery exists."""
        for picking in self:
            picking.has_pod = bool(picking.proof_of_delivery or picking.pod_signed_by)

    @api.onchange("proof_of_delivery", "pod_signed_by")
    def _onchange_pod_fields(self):
        """Auto-populates pod_timestamp when proof or receiver is recorded without timestamp."""
        if (self.proof_of_delivery or self.pod_signed_by) and not self.pod_timestamp:
            self.pod_timestamp = fields.Datetime.now()

    @api.model_create_multi
    def create(self, vals_list):
        """Overrides create to ensure pod_timestamp is populated if POD fields are supplied."""
        for vals in vals_list:
            if (
                vals.get("proof_of_delivery") or vals.get("pod_signed_by")
            ) and not vals.get("pod_timestamp"):
                vals["pod_timestamp"] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        """Overrides write to ensure pod_timestamp is populated if POD fields are supplied without timestamp."""
        if (
            "proof_of_delivery" in vals or "pod_signed_by" in vals
        ) and "pod_timestamp" not in vals:
            for picking in self:
                if not picking.pod_timestamp and (
                    vals.get("proof_of_delivery") or vals.get("pod_signed_by")
                ):
                    vals["pod_timestamp"] = fields.Datetime.now()
                    break
        return super().write(vals)

    @api.onchange("vehicle_id")
    def _onchange_vehicle_id(self):
        """Auto-populates driver from assigned vehicle default driver."""
        if self.vehicle_id and self.vehicle_id.driver_id:
            self.driver_id = self.vehicle_id.driver_id

    @api.depends(
        "move_ids.product_uom_qty",
        "move_ids.product_id.weight",
        "move_ids.product_id.volume",
        "move_ids.state",
    )
    def _compute_total_weight_volume(self):
        """Computes accumulated weight and volume of all non-cancelled stock moves."""
        for picking in self:
            weight = 0.0
            volume = 0.0
            for move in picking.move_ids.filtered(lambda m: m.state != "cancel"):
                qty = move.product_uom_qty or 0.0
                prod = move.product_id
                if prod:
                    weight += (prod.weight or 0.0) * qty
                    volume += (prod.volume or 0.0) * qty
            picking.total_weight = weight
            picking.total_volume = volume

    @api.constrains("vehicle_id", "total_weight", "total_volume")
    def _check_vehicle_capacity(self):
        """Enforces vehicle cargo capacity limits against aggregated weight and volume."""
        for picking in self:
            if not picking.vehicle_id:
                continue
            v = picking.vehicle_id
            if v.max_weight > 0.0 and picking.total_weight > v.max_weight:
                raise ValidationError(
                    f"Overcapacity Error: Total weight ({picking.total_weight:.2f} kg) "
                    f"exceeds vehicle maximum weight capacity ({v.max_weight:.2f} kg) "
                    f"for vehicle '{v.license_plate}'."
                )
            if v.max_volume > 0.0 and picking.total_volume > v.max_volume:
                raise ValidationError(
                    f"Overcapacity Error: Total volume ({picking.total_volume:.4f} m³) "
                    f"exceeds vehicle maximum volume capacity ({v.max_volume:.4f} m³) "
                    f"for vehicle '{v.license_plate}'."
                )

    def action_mark_synced(self):
        """Marks picking record as synced to SAP."""
        return self.write({"sap_sync_status": SYNC_STATUS_SYNCED})

    def action_mark_failed(self):
        """Marks picking record as sync failed."""
        return self.write({"sap_sync_status": SYNC_STATUS_FAILED})

    def _generate_sync_ref(self, prefix=REF_PREFIX_GOODS_RECEIPT):
        """Generates unique transaction reference: SYNC-{prefix}-YYYYMMDD-XXXXXX."""
        date_str = datetime.now().strftime("%Y%m%d")
        short_id = uuid.uuid4().hex[:6].upper()
        return f"SYNC-{prefix}-{date_str}-{short_id}"

    def _send_sap_goods_receipt_webhook(self):
        """Sends Goods Receipt confirmation webhook HTTP POST to SAP Upper Line.

        Formats payload as:
        {
            "sap_doc_number": self.sap_doc_number,
            "status": "GOODS_RECEIVED",
            "received_date": "YYYY-MM-DDTHH:MM:SSZ",
            "warehouse_code": warehouse_code
        }
        Captures the response (including sap_accounting_log) and writes to sap.sync.log.
        Updates self.sap_sync_status to synced on success or failed on error.
        Ensures fail-safe, non-blocking execution so physical stock movement is not blocked.
        """
        for picking in self:
            if not picking.sap_doc_number:
                continue

            sync_ref = picking._generate_sync_ref(REF_PREFIX_GOODS_RECEIPT)
            sap_base_url = (
                picking.env["ir.config_parameter"]
                .sudo()
                .get_param(CONFIG_PARAM_SAP_BASE_URL)
            )
            sap_api_token = (
                picking.env["ir.config_parameter"]
                .sudo()
                .get_param(CONFIG_PARAM_SAP_API_TOKEN)
            )

            warehouse_code = False
            if picking.picking_type_id and picking.picking_type_id.warehouse_id:
                warehouse_code = picking.picking_type_id.warehouse_id.code
            if not warehouse_code:
                warehouse_code = picking.company_id.name or "DEFAULT_WH"

            received_date = (picking.date_done or fields.Datetime.now()).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            payload = {
                "sap_doc_number": picking.sap_doc_number,
                "status": WEBHOOK_STATUS_GOODS_RECEIVED,
                "received_date": received_date,
                "warehouse_code": warehouse_code,
            }
            payload_str = json.dumps(payload)

            if not sap_base_url:
                err_msg = "SAP Base URL not configured in system settings."
                _logger.warning("Picking %s webhook aborted: %s", picking.name, err_msg)
                picking.sudo().write({"sap_sync_status": SYNC_STATUS_FAILED})
                picking.env["sap.sync.log"].sudo().create(
                    {
                        "name": sync_ref,
                        "sync_type": SYNC_TYPE_INBOUND_PO,
                        "direction": DIRECTION_OUTBOUND,
                        "payload": payload_str,
                        "status": SYNC_STATUS_FAILED,
                        "error_message": err_msg,
                        "sync_date": fields.Datetime.now(),
                    }
                )
                continue

            endpoint_url = sap_base_url.rstrip("/") + SAP_ENDPOINT_GOODS_RECEIPT
            headers = {
                "Content-Type": "application/json",
            }
            if sap_api_token:
                headers[HTTP_HEADER_AUTHORIZATION] = (
                    f"{AUTH_BEARER_PREFIX}{sap_api_token}"
                )
                headers[HTTP_HEADER_API_KEY] = sap_api_token

            try:
                response = requests.post(
                    endpoint_url,
                    data=payload_str,
                    headers=headers,
                    timeout=WEBHOOK_TIMEOUT_SECONDS,
                )
                resp_text = response.text
                if response.status_code in (200, 201):
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
                            "payload": resp_text,
                            "status": SYNC_STATUS_SUCCESS,
                            "error_message": False,
                            "sync_date": fields.Datetime.now(),
                        }
                    )
                else:
                    err_msg = f"HTTP {response.status_code}: {resp_text}"
                    _logger.warning(
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
                            "status": SYNC_STATUS_FAILED,
                            "error_message": err_msg,
                            "sync_date": fields.Datetime.now(),
                        }
                    )
            except Exception as exc:
                err_msg = f"Connection error: {exc!s}"
                _logger.exception(
                    "Failed to send Goods Receipt webhook for %s: %s",
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
                        "status": SYNC_STATUS_FAILED,
                        "error_message": err_msg,
                        "sync_date": fields.Datetime.now(),
                    }
                )

    def action_send_sap_goods_receipt_webhook(self):
        """Action button to manually trigger or retry Goods Receipt webhook transmission."""
        self.ensure_one()
        self._send_sap_goods_receipt_webhook()
        return True

    def _action_done(self):
        """Overrides _action_done to trigger Goods Receipt webhook for completed incoming pickings."""
        res = super()._action_done()
        for picking in self:
            if (
                picking.picking_type_id.code == PICKING_TYPE_CODE_INCOMING
                and picking.sap_doc_number
            ):
                picking._send_sap_goods_receipt_webhook()
        return res

    @api.model
    def create_inbound_from_sap(self, payload_dict):
        """Creates an incoming stock picking and stock moves from SAP PO payload.

        Validates vendor and material items, performs idempotent check, resolves
        appropriate warehouse and location records, batch-creates moves, and confirms
        the picking to 'assigned' state.

        Args:
            payload_dict (dict): Parsed JSON body containing SAP PO details.

        Returns:
            tuple: (picking_record: stock.picking, is_created: bool)

        Raises:
            ValueError: If payload is missing mandatory fields or references nonexistent records.
        """
        sap_doc_number = payload_dict.get("sap_doc_number")
        vendor_code = payload_dict.get("vendor_code")
        items = payload_dict.get("items")

        if (
            not sap_doc_number
            or not isinstance(sap_doc_number, str)
            or not sap_doc_number.strip()
        ):
            raise ValueError(
                "Bad Request: Missing or invalid mandatory field 'sap_doc_number'"
            )

        if (
            not vendor_code
            or not isinstance(vendor_code, str)
            or not vendor_code.strip()
        ):
            raise ValueError(
                "Bad Request: Missing or invalid mandatory field 'vendor_code'"
            )

        if not isinstance(items, list) or len(items) == 0:
            raise ValueError("Bad Request: Missing or empty 'items' array")

        sap_doc_number = sap_doc_number.strip()
        vendor_code_clean = vendor_code.strip()

        # Idempotency check
        existing_picking = self.search(
            [
                ("sap_doc_number", "=", sap_doc_number),
                ("state", "!=", PICKING_STATE_CANCEL),
            ],
            limit=1,
        )
        if existing_picking:
            return existing_picking, False

        # Vendor resolution
        vendor = (
            self.env["res.partner"]
            .sudo()
            .search(
                [("sap_partner_code", "=", vendor_code_clean)],
                limit=1,
            )
        )
        if not vendor:
            raise ValueError(
                f"Bad Request: Vendor with SAP partner code '{vendor_code_clean}' not found"
            )

        # Warehouse and picking type resolution
        warehouse_code = payload_dict.get("warehouse_code") or payload_dict.get(
            "plant_code"
        )
        picking_type_obj = self.env["stock.picking.type"].sudo()
        warehouse_obj = self.env["stock.warehouse"].sudo()

        picking_type = None
        if warehouse_code and isinstance(warehouse_code, str):
            wh_code_clean = warehouse_code.strip()
            wh = warehouse_obj.search(
                ["|", ("code", "=", wh_code_clean), ("name", "ilike", wh_code_clean)],
                limit=1,
            )
            if wh:
                picking_type = picking_type_obj.search(
                    [
                        ("warehouse_id", "=", wh.id),
                        ("code", "=", PICKING_TYPE_CODE_INCOMING),
                    ],
                    limit=1,
                )

        if not picking_type:
            company = self.env.company
            wh = warehouse_obj.search([("company_id", "=", company.id)], limit=1)
            if wh:
                picking_type = picking_type_obj.search(
                    [
                        ("warehouse_id", "=", wh.id),
                        ("code", "=", PICKING_TYPE_CODE_INCOMING),
                    ],
                    limit=1,
                )

        if not picking_type:
            picking_type = picking_type_obj.search(
                [
                    ("code", "=", PICKING_TYPE_CODE_INCOMING),
                    ("company_id", "in", (self.env.company.id, False)),
                ],
                limit=1,
            )

        if not picking_type:
            raise ValueError(
                "Incoming operation type (stock.picking.type) not configured in the system."
            )

        # Source supplier location resolution
        supplier_loc = self.env.ref(
            "stock.stock_location_suppliers", raise_if_not_found=False
        )
        if not supplier_loc:
            supplier_loc = (
                self.env["stock.location"]
                .sudo()
                .search(
                    [
                        ("usage", "=", "supplier"),
                        ("company_id", "in", (picking_type.company_id.id, False)),
                    ],
                    limit=1,
                )
            )
        location_id = (
            supplier_loc.id if supplier_loc else picking_type.default_location_src_id.id
        )
        if not location_id:
            raise ValueError("Supplier source location not configured.")

        # Destination internal location resolution
        dest_location_id = picking_type.default_location_dest_id.id
        if not dest_location_id and picking_type.warehouse_id:
            dest_location_id = picking_type.warehouse_id.lot_stock_id.id
        if not dest_location_id:
            dest_location = (
                self.env["stock.location"]
                .sudo()
                .search(
                    [
                        ("usage", "=", "internal"),
                        ("company_id", "in", (picking_type.company_id.id, False)),
                    ],
                    limit=1,
                )
            )
            dest_location_id = dest_location.id if dest_location else False
        if not dest_location_id:
            raise ValueError("Internal destination location not configured.")

        # Batch validation of material items
        product_obj = self.env["product.product"].sudo()
        mat_codes = set()
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                raise TypeError(f"Bad Request: Item #{idx + 1} must be a JSON object")
            code = item.get("sap_material_code")
            if not code or not str(code).strip():
                raise ValueError(
                    f"Bad Request: Item #{idx + 1} missing mandatory field 'sap_material_code'"
                )
            mat_codes.add(str(code).strip())

        products = product_obj.search([("sap_material_code", "in", list(mat_codes))])
        prod_map = {p.sap_material_code: p for p in products}

        validated_moves_data = []
        uom_obj = self.env["uom.uom"].sudo()
        for idx, item in enumerate(items):
            code = str(item.get("sap_material_code")).strip()
            product = prod_map.get(code)
            if not product:
                raise ValueError(
                    f"Bad Request: Material with SAP material code '{code}' not found"
                )

            qty = item.get("qty")
            if qty is None:
                raise ValueError(
                    f"Bad Request: Item #{idx + 1} missing mandatory field 'qty'"
                )

            try:
                qty_val = float(qty)
                if qty_val <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError(
                    f"Bad Request: Item #{idx + 1} ({code}) 'qty' must be greater than 0"
                )

            target_uom = product.uom_id
            uom_str = item.get("uom")
            if uom_str and isinstance(uom_str, str):
                found_uom = uom_obj.search(
                    [
                        "|",
                        ("name", "=ilike", uom_str.strip()),
                        ("category_id", "=", product.uom_id.category_id.id),
                    ],
                    limit=1,
                )
                if found_uom:
                    target_uom = found_uom
                else:
                    _logger.warning(
                        "UoM '%s' not found for material '%s', defaulting to '%s'",
                        uom_str,
                        code,
                        product.uom_id.name,
                    )

            validated_moves_data.append(
                {
                    "product": product,
                    "qty": qty_val,
                    "uom": target_uom,
                }
            )

        # Scheduled date resolution
        scheduled_date = fields.Datetime.now()
        expected_date_str = payload_dict.get("expected_date")
        if expected_date_str and isinstance(expected_date_str, str):
            try:
                clean_date = expected_date_str.strip()
                if "T" in clean_date:
                    clean_date = clean_date.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(clean_date)
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                    scheduled_date = dt
                else:
                    parsed_date = datetime.strptime(clean_date, "%Y-%m-%d").date()
                    scheduled_date = datetime.combine(parsed_date, time.min)
            except (ValueError, TypeError) as dt_err:
                _logger.warning(
                    "Could not parse expected_date '%s', falling back to now(): %s",
                    expected_date_str,
                    dt_err,
                )

        # Create picking header
        picking_vals = {
            "picking_type_id": picking_type.id,
            "partner_id": vendor.id,
            "location_id": location_id,
            "location_dest_id": dest_location_id,
            "origin": sap_doc_number,
            "sap_doc_number": sap_doc_number,
            "sap_sync_status": SYNC_STATUS_DRAFT,
            "scheduled_date": scheduled_date,
            "company_id": picking_type.company_id.id,
        }
        picking = self.sudo().create(picking_vals)

        # Batch create moves
        move_vals_list = [
            {
                "name": vdata["product"].display_name or vdata["product"].name,
                "product_id": vdata["product"].id,
                "product_uom_qty": vdata["qty"],
                "product_uom": vdata["uom"].id,
                "picking_id": picking.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": picking.company_id.id,
            }
            for vdata in validated_moves_data
        ]
        self.env["stock.move"].sudo().create(move_vals_list)

        # Transition picking to assigned (Ready)
        picking.action_confirm()
        if picking.state == PICKING_STATE_CONFIRMED:
            picking.action_assign()

        if picking.move_line_ids:
            picking.move_line_ids._apply_putaway_strategy()

        return picking, True

    @api.model
    def create_outbound_from_sap(self, payload_dict):
        """Creates an outgoing stock picking (Delivery Order) and stock moves from SAP DO payload.

        Validates customer and material items, performs idempotent check, resolves
        appropriate warehouse and location records, batch-creates moves, and confirms
        the picking to 'assigned' or 'confirmed' state.

        Args:
            payload_dict (dict): Parsed JSON body containing SAP Delivery Order details.

        Returns:
            tuple: (picking_record: stock.picking, is_created: bool)

        Raises:
            ValueError: If payload is missing mandatory fields or references nonexistent records.
        """
        sap_doc_number = payload_dict.get("sap_doc_number")
        customer_code = payload_dict.get("customer_code")
        items = payload_dict.get("items")

        if (
            not sap_doc_number
            or not isinstance(sap_doc_number, str)
            or not sap_doc_number.strip()
        ):
            raise ValueError(
                "Bad Request: Missing or invalid mandatory field 'sap_doc_number'"
            )

        if (
            not customer_code
            or not isinstance(customer_code, str)
            or not customer_code.strip()
        ):
            raise ValueError(
                "Bad Request: Missing or invalid mandatory field 'customer_code'"
            )

        if not isinstance(items, list) or len(items) == 0:
            raise ValueError("Bad Request: Missing or empty 'items' array")

        sap_doc_number = sap_doc_number.strip()
        customer_code_clean = customer_code.strip()

        # Idempotency check: lookup existing outgoing picking for this sap_doc_number
        existing_picking = self.search(
            [
                ("sap_doc_number", "=", sap_doc_number),
                ("picking_type_id.code", "=", PICKING_TYPE_CODE_OUTGOING),
                ("state", "!=", PICKING_STATE_CANCEL),
            ],
            limit=1,
        )
        if existing_picking:
            return existing_picking, False

        # Customer resolution
        customer = (
            self.env["res.partner"]
            .sudo()
            .search(
                [("sap_partner_code", "=", customer_code_clean)],
                limit=1,
            )
        )
        if not customer:
            raise ValueError(
                f"Bad Request: Customer with SAP partner code '{customer_code_clean}' not found"
            )

        # Warehouse and picking type resolution (outgoing)
        warehouse_code = payload_dict.get("warehouse_code") or payload_dict.get(
            "plant_code"
        )
        picking_type_obj = self.env["stock.picking.type"].sudo()
        warehouse_obj = self.env["stock.warehouse"].sudo()

        picking_type = None
        if warehouse_code and isinstance(warehouse_code, str):
            wh_code_clean = warehouse_code.strip()
            wh = warehouse_obj.search(
                ["|", ("code", "=", wh_code_clean), ("name", "ilike", wh_code_clean)],
                limit=1,
            )
            if wh:
                picking_type = picking_type_obj.search(
                    [
                        ("warehouse_id", "=", wh.id),
                        ("code", "=", PICKING_TYPE_CODE_OUTGOING),
                    ],
                    limit=1,
                )

        if not picking_type:
            company = self.env.company
            wh = warehouse_obj.search([("company_id", "=", company.id)], limit=1)
            if wh:
                picking_type = picking_type_obj.search(
                    [
                        ("warehouse_id", "=", wh.id),
                        ("code", "=", PICKING_TYPE_CODE_OUTGOING),
                    ],
                    limit=1,
                )

        if not picking_type:
            picking_type = picking_type_obj.search(
                [
                    ("code", "=", PICKING_TYPE_CODE_OUTGOING),
                    ("company_id", "in", (self.env.company.id, False)),
                ],
                limit=1,
            )

        if not picking_type:
            raise ValueError(
                "Outgoing delivery operation type (stock.picking.type) not configured in the system."
            )

        # Source internal location resolution
        location_id = picking_type.default_location_src_id.id
        if not location_id and picking_type.warehouse_id:
            location_id = picking_type.warehouse_id.lot_stock_id.id
        if not location_id:
            source_loc = (
                self.env["stock.location"]
                .sudo()
                .search(
                    [
                        ("usage", "=", "internal"),
                        ("company_id", "in", (picking_type.company_id.id, False)),
                    ],
                    limit=1,
                )
            )
            location_id = source_loc.id if source_loc else False
        if not location_id:
            raise ValueError("Internal source stock location not configured.")

        # Destination customer location resolution
        customer_loc = self.env.ref(
            "stock.stock_location_customers", raise_if_not_found=False
        )
        if not customer_loc:
            customer_loc = (
                self.env["stock.location"]
                .sudo()
                .search(
                    [
                        ("usage", "=", "customer"),
                        ("company_id", "in", (picking_type.company_id.id, False)),
                    ],
                    limit=1,
                )
            )
        dest_location_id = (
            customer_loc.id
            if customer_loc
            else (
                customer.property_stock_customer.id
                if customer.property_stock_customer
                else picking_type.default_location_dest_id.id
            )
        )
        if not dest_location_id:
            raise ValueError("Customer destination location not configured.")

        # Batch validation of material items
        product_obj = self.env["product.product"].sudo()
        mat_codes = set()
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                raise TypeError(f"Bad Request: Item #{idx + 1} must be a JSON object")
            code = item.get("sap_material_code")
            if not code or not str(code).strip():
                raise ValueError(
                    f"Bad Request: Item #{idx + 1} missing mandatory field 'sap_material_code'"
                )
            mat_codes.add(str(code).strip())

        products = product_obj.search([("sap_material_code", "in", list(mat_codes))])
        prod_map = {p.sap_material_code: p for p in products}

        validated_moves_data = []
        uom_obj = self.env["uom.uom"].sudo()
        for idx, item in enumerate(items):
            code = str(item.get("sap_material_code")).strip()
            product = prod_map.get(code)
            if not product:
                raise ValueError(
                    f"Bad Request: Material with SAP material code '{code}' not found"
                )

            qty = item.get("qty")
            if qty is None:
                raise ValueError(
                    f"Bad Request: Item #{idx + 1} missing mandatory field 'qty'"
                )

            try:
                qty_val = float(qty)
                if qty_val <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError(
                    f"Bad Request: Item #{idx + 1} ({code}) 'qty' must be greater than 0"
                )

            target_uom = product.uom_id
            uom_str = item.get("uom")
            if uom_str and isinstance(uom_str, str):
                found_uom = uom_obj.search(
                    [
                        "|",
                        ("name", "=ilike", uom_str.strip()),
                        ("category_id", "=", product.uom_id.category_id.id),
                    ],
                    limit=1,
                )
                if found_uom:
                    target_uom = found_uom
                else:
                    _logger.warning(
                        "UoM '%s' not found for material '%s', defaulting to '%s'",
                        uom_str,
                        code,
                        product.uom_id.name,
                    )

            validated_moves_data.append(
                {
                    "product": product,
                    "qty": qty_val,
                    "uom": target_uom,
                }
            )

        # Scheduled date resolution
        scheduled_date = fields.Datetime.now()
        expected_date_str = payload_dict.get("expected_date") or payload_dict.get(
            "scheduled_date"
        )
        if expected_date_str and isinstance(expected_date_str, str):
            try:
                clean_date = expected_date_str.strip()
                if "T" in clean_date:
                    clean_date = clean_date.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(clean_date)
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                    scheduled_date = dt
                else:
                    parsed_date = datetime.strptime(clean_date, "%Y-%m-%d").date()
                    scheduled_date = datetime.combine(parsed_date, time.min)
            except (ValueError, TypeError) as dt_err:
                _logger.warning(
                    "Could not parse expected_date '%s', falling back to now(): %s",
                    expected_date_str,
                    dt_err,
                )

        # Create picking header
        picking_vals = {
            "picking_type_id": picking_type.id,
            "partner_id": customer.id,
            "location_id": location_id,
            "location_dest_id": dest_location_id,
            "origin": sap_doc_number,
            "sap_doc_number": sap_doc_number,
            "sap_sync_status": SYNC_STATUS_DRAFT,
            "scheduled_date": scheduled_date,
            "company_id": picking_type.company_id.id,
        }
        picking = self.sudo().create(picking_vals)

        # Batch create moves
        move_vals_list = [
            {
                "name": vdata["product"].display_name or vdata["product"].name,
                "product_id": vdata["product"].id,
                "product_uom_qty": vdata["qty"],
                "product_uom": vdata["uom"].id,
                "picking_id": picking.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": picking.company_id.id,
            }
            for vdata in validated_moves_data
        ]
        self.env["stock.move"].sudo().create(move_vals_list)

        # Transition picking to confirmed and try to reserve stock
        picking.action_confirm()
        if picking.state == PICKING_STATE_CONFIRMED:
            picking.action_assign()

        return picking, True
