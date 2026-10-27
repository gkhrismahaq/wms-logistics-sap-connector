"""Inbound Purchase Order domain service."""

import logging

from psycopg2 import IntegrityError

from ..constants import (
    ERR_EMPTY_ITEMS,
    ERR_MISSING_DOC_NUMBER,
    ERR_MISSING_VENDOR_CODE,
    PICKING_STATE_CANCEL,
    PICKING_STATE_CONFIRMED,
    PICKING_TYPE_CODE_INCOMING,
    SYNC_STATUS_DRAFT,
)
from .sap_resolver_service import (
    parse_scheduled_date,
    resolve_company,
    resolve_source_and_dest_locations,
    resolve_warehouse_and_picking_type,
    validate_and_resolve_material_items,
)

_logger = logging.getLogger(__name__)


def process_inbound_po(picking_model, payload_dict):
    """Processes SAP Inbound PO payload and creates corresponding stock picking."""
    sap_doc_number = payload_dict.get("sap_doc_number")
    vendor_code = payload_dict.get("vendor_code")
    items = payload_dict.get("items")

    if (
        not sap_doc_number
        or not isinstance(sap_doc_number, str)
        or not sap_doc_number.strip()
    ):
        raise ValueError(ERR_MISSING_DOC_NUMBER)

    if not vendor_code or not isinstance(vendor_code, str) or not vendor_code.strip():
        raise ValueError(ERR_MISSING_VENDOR_CODE)

    if not isinstance(items, list) or len(items) == 0:
        raise ValueError(ERR_EMPTY_ITEMS)

    sap_doc_number = sap_doc_number.strip()
    vendor_code_clean = vendor_code.strip()

    # Multi-company resolution
    company = resolve_company(picking_model.env, payload_dict.get("company_code"))
    env = picking_model.with_company(company).env

    # Idempotency check: lookup existing active picking
    existing_picking = env["stock.picking"].search(
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
        env["res.partner"]
        .sudo()
        .search([("sap_partner_code", "=", vendor_code_clean)], limit=1)
    )
    if not vendor:
        raise ValueError(
            f"Bad Request: Vendor with SAP partner code '{vendor_code_clean}' not found"
        )

    # Warehouse and operation type resolution
    warehouse_code = payload_dict.get("warehouse_code") or payload_dict.get(
        "plant_code"
    )
    picking_type = resolve_warehouse_and_picking_type(
        env,
        warehouse_code=warehouse_code,
        picking_type_code=PICKING_TYPE_CODE_INCOMING,
        company=company,
    )

    # Locations resolution
    location_id, dest_location_id = resolve_source_and_dest_locations(
        env,
        picking_type=picking_type,
        partner=vendor,
        is_inbound=True,
    )

    # Material items resolution
    validated_moves_data = validate_and_resolve_material_items(env, items)

    # Scheduled date resolution
    scheduled_date = parse_scheduled_date(payload_dict.get("expected_date"))

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

    try:
        with env.cr.savepoint():
            picking = env["stock.picking"].sudo().create(picking_vals)
    except IntegrityError:
        # Recover gracefully if concurrent thread created the same sap_doc_number
        recovered = env["stock.picking"].search(
            [("sap_doc_number", "=", sap_doc_number)], limit=1
        )
        if recovered:
            return recovered, False
        raise

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
    env["stock.move"].sudo().create(move_vals_list)

    picking.action_confirm()
    if picking.state == PICKING_STATE_CONFIRMED:
        picking.action_assign()

    if picking.move_line_ids:
        picking.move_line_ids._apply_putaway_strategy()

    return picking, True
