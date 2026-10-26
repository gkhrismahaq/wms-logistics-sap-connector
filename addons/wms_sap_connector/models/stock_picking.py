# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time

from odoo import api, fields, models
from ..constants import (
    PICKING_STATE_ASSIGNED,
    PICKING_STATE_CANCEL,
    PICKING_STATE_CONFIRMED,
    PICKING_TYPE_CODE_INCOMING,
    SAP_PICKING_SYNC_STATUS_SELECTION,
    SYNC_STATUS_DRAFT,
    SYNC_STATUS_FAILED,
    SYNC_STATUS_SYNCED,
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

    _sql_constraints = [
        (
            "sap_doc_number_uniq",
            "unique(sap_doc_number)",
            "The SAP document number must be unique across all transfer documents.",
        ),
    ]

    def action_mark_synced(self):
        """Marks picking record as synced to SAP."""
        return self.write({"sap_sync_status": SYNC_STATUS_SYNCED})

    def action_mark_failed(self):
        """Marks picking record as sync failed."""
        return self.write({"sap_sync_status": SYNC_STATUS_FAILED})

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

        if not sap_doc_number or not isinstance(sap_doc_number, str) or not sap_doc_number.strip():
            raise ValueError("Bad Request: Missing or invalid mandatory field 'sap_doc_number'")

        if not vendor_code or not isinstance(vendor_code, str) or not vendor_code.strip():
            raise ValueError("Bad Request: Missing or invalid mandatory field 'vendor_code'")

        if not isinstance(items, list) or len(items) == 0:
            raise ValueError("Bad Request: Missing or empty 'items' array")

        sap_doc_number = sap_doc_number.strip()
        vendor_code_clean = vendor_code.strip()

        # Idempotency check
        existing_picking = self.search(
            [("sap_doc_number", "=", sap_doc_number), ("state", "!=", PICKING_STATE_CANCEL)],
            limit=1,
        )
        if existing_picking:
            return existing_picking, False

        # Vendor resolution
        vendor = self.env["res.partner"].sudo().search(
            [("sap_partner_code", "=", vendor_code_clean)],
            limit=1,
        )
        if not vendor:
            raise ValueError(f"Bad Request: Vendor with SAP partner code '{vendor_code_clean}' not found")

        # Warehouse and picking type resolution
        warehouse_code = payload_dict.get("warehouse_code") or payload_dict.get("plant_code")
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
                    [("warehouse_id", "=", wh.id), ("code", "=", PICKING_TYPE_CODE_INCOMING)],
                    limit=1,
                )

        if not picking_type:
            company = self.env.company
            wh = warehouse_obj.search([("company_id", "=", company.id)], limit=1)
            if wh:
                picking_type = picking_type_obj.search(
                    [("warehouse_id", "=", wh.id), ("code", "=", PICKING_TYPE_CODE_INCOMING)],
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
            raise ValueError("Incoming operation type (stock.picking.type) not configured in the system.")

        # Source supplier location resolution
        supplier_loc = self.env.ref("stock.stock_location_suppliers", raise_if_not_found=False)
        if not supplier_loc:
            supplier_loc = self.env["stock.location"].sudo().search(
                [("usage", "=", "supplier"), ("company_id", "in", (picking_type.company_id.id, False))],
                limit=1,
            )
        location_id = supplier_loc.id if supplier_loc else picking_type.default_location_src_id.id
        if not location_id:
            raise ValueError("Supplier source location not configured.")

        # Destination internal location resolution
        dest_location_id = picking_type.default_location_dest_id.id
        if not dest_location_id and picking_type.warehouse_id:
            dest_location_id = picking_type.warehouse_id.lot_stock_id.id
        if not dest_location_id:
            dest_location = self.env["stock.location"].sudo().search(
                [("usage", "=", "internal"), ("company_id", "in", (picking_type.company_id.id, False))],
                limit=1,
            )
            dest_location_id = dest_location.id if dest_location else False
        if not dest_location_id:
            raise ValueError("Internal destination location not configured.")

        # Batch validation of material items
        product_obj = self.env["product.product"].sudo()
        mat_codes = set()
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(f"Bad Request: Item #{idx + 1} must be a JSON object")
            code = item.get("sap_material_code")
            if not code or not str(code).strip():
                raise ValueError(f"Bad Request: Item #{idx + 1} missing mandatory field 'sap_material_code'")
            mat_codes.add(str(code).strip())

        products = product_obj.search([("sap_material_code", "in", list(mat_codes))])
        prod_map = {p.sap_material_code: p for p in products}

        validated_moves_data = []
        uom_obj = self.env["uom.uom"].sudo()
        for idx, item in enumerate(items):
            code = str(item.get("sap_material_code")).strip()
            product = prod_map.get(code)
            if not product:
                raise ValueError(f"Bad Request: Material with SAP material code '{code}' not found")

            qty = item.get("qty")
            if qty is None:
                raise ValueError(f"Bad Request: Item #{idx + 1} missing mandatory field 'qty'")

            try:
                qty_val = float(qty)
                if qty_val <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError(f"Bad Request: Item #{idx + 1} ({code}) 'qty' must be greater than 0")

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

            validated_moves_data.append({
                "product": product,
                "qty": qty_val,
                "uom": target_uom,
            })

        # Scheduled date resolution
        scheduled_date = fields.Datetime.now()
        expected_date_str = payload_dict.get("expected_date")
        if expected_date_str and isinstance(expected_date_str, str):
            try:
                clean_date = expected_date_str.strip()
                if "T" in clean_date:
                    clean_date = clean_date.replace("Z", "+00:00")
                    scheduled_date = datetime.fromisoformat(clean_date)
                else:
                    parsed_date = datetime.strptime(clean_date, "%Y-%m-%d").date()
                    scheduled_date = datetime.combine(parsed_date, time.min)
            except Exception as dt_err:
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

        return picking, True
