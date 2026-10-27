"""Outbound Delivery Order domain service."""

import logging

from psycopg2 import IntegrityError

from ..constants import (
    ERR_EMPTY_ITEMS,
    ERR_MISSING_CUSTOMER_CODE,
    ERR_MISSING_DOC_NUMBER,
    PICKING_STATE_CANCEL,
    PICKING_STATE_CONFIRMED,
    PICKING_TYPE_CODE_OUTGOING,
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


def process_outbound_delivery(picking_model, payload_dict):
    """Processes SAP Outbound DO payload and creates corresponding stock picking."""
    sap_doc_number = payload_dict.get("sap_doc_number")
    customer_code = payload_dict.get("customer_code")
    items = payload_dict.get("items")

    if (
        not sap_doc_number
        or not isinstance(sap_doc_number, str)
        or not sap_doc_number.strip()
    ):
        raise ValueError(ERR_MISSING_DOC_NUMBER)

    if (
        not customer_code
        or not isinstance(customer_code, str)
        or not customer_code.strip()
    ):
        raise ValueError(ERR_MISSING_CUSTOMER_CODE)

    if not isinstance(items, list) or len(items) == 0:
        raise ValueError(ERR_EMPTY_ITEMS)

    sap_doc_number = sap_doc_number.strip()
    customer_code_clean = customer_code.strip()

    # Multi-company resolution
    company = resolve_company(picking_model.env, payload_dict.get("company_code"))
    env = picking_model.with_company(company).env

    # Idempotency check: lookup existing active picking
    existing_picking = env["stock.picking"].search(
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
        env["res.partner"]
        .sudo()
        .search([("sap_partner_code", "=", customer_code_clean)], limit=1)
    )
    if not customer:
        raise ValueError(
            f"Bad Request: Customer with SAP partner code '{customer_code_clean}' not found"
        )

    # Warehouse and operation type resolution
    warehouse_code = payload_dict.get("warehouse_code") or payload_dict.get(
        "plant_code"
    )
    picking_type = resolve_warehouse_and_picking_type(
        env,
        warehouse_code=warehouse_code,
        picking_type_code=PICKING_TYPE_CODE_OUTGOING,
        company=company,
    )

    # Locations resolution
    location_id, dest_location_id = resolve_source_and_dest_locations(
        env,
        picking_type=picking_type,
        partner=customer,
        is_inbound=False,
    )

    # Material items resolution
    validated_moves_data = validate_and_resolve_material_items(env, items)

    # Scheduled date resolution
    expected_date_str = payload_dict.get("expected_date") or payload_dict.get(
        "scheduled_date"
    )
    scheduled_date = parse_scheduled_date(expected_date_str)

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

    try:
        with env.cr.savepoint():
            picking = env["stock.picking"].sudo().create(picking_vals)
    except IntegrityError:
        # Recover gracefully if concurrent thread created the same sap_doc_number
        recovered = env["stock.picking"].search(
            [
                ("sap_doc_number", "=", sap_doc_number),
                ("picking_type_id.code", "=", PICKING_TYPE_CODE_OUTGOING),
            ],
            limit=1,
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

    return picking, True
