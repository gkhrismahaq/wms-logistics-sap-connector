"""Resolver helper service for warehouse, locations, materials, and dates."""

import logging
from datetime import datetime, time, timezone

from odoo import fields

from ..constants import (
    DATE_FMT_DATE_ONLY,
    ERR_DEST_LOCATION_NOT_CONFIGURED,
    ERR_MATERIAL_NOT_FOUND,
    ERR_OPERATION_TYPE_NOT_CONFIGURED,
    ERR_QTY_MUST_BE_POSITIVE,
    ERR_SRC_LOCATION_NOT_CONFIGURED,
)

_logger = logging.getLogger(__name__)


def resolve_company(env, company_code=None):
    """Resolves target res.company by company_code or falls back to env.company."""
    if company_code and isinstance(company_code, str):
        clean_code = company_code.strip()
        found_company = (
            env["res.company"]
            .sudo()
            .search(
                [
                    "|",
                    ("code", "=ilike", clean_code),
                    ("name", "=ilike", clean_code),
                ],
                limit=1,
            )
        )
        if found_company:
            return found_company
    return env.company


def resolve_warehouse_and_picking_type(
    env, warehouse_code, picking_type_code, company=None
):
    """Resolves picking operation type by warehouse code and operation code."""
    picking_type_obj = env["stock.picking.type"].sudo()
    warehouse_obj = env["stock.warehouse"].sudo()
    company = company or env.company

    picking_type = None
    if warehouse_code and isinstance(warehouse_code, str):
        wh_code_clean = warehouse_code.strip()
        wh = warehouse_obj.search(
            [
                ("company_id", "=", company.id),
                "|",
                ("code", "=ilike", wh_code_clean),
                ("name", "=ilike", wh_code_clean),
            ],
            limit=1,
        )
        if wh:
            picking_type = picking_type_obj.search(
                [
                    ("warehouse_id", "=", wh.id),
                    ("code", "=", picking_type_code),
                ],
                limit=1,
            )

    if not picking_type:
        wh = warehouse_obj.search([("company_id", "=", company.id)], limit=1)
        if wh:
            picking_type = picking_type_obj.search(
                [
                    ("warehouse_id", "=", wh.id),
                    ("code", "=", picking_type_code),
                ],
                limit=1,
            )

    if not picking_type:
        picking_type = picking_type_obj.search(
            [
                ("code", "=", picking_type_code),
                ("company_id", "in", (company.id, False)),
            ],
            limit=1,
        )

    if not picking_type:
        raise ValueError(ERR_OPERATION_TYPE_NOT_CONFIGURED)

    return picking_type


def resolve_source_and_dest_locations(env, picking_type, partner, is_inbound=True):
    """Resolves source and destination stock locations for transfer documents."""
    company_id = picking_type.company_id.id if picking_type.company_id else False

    if is_inbound:
        # Supplier source location: prioritize vendor's configured location
        src_location_id = (
            partner.property_stock_supplier.id
            if partner.property_stock_supplier
            else False
        )
        if not src_location_id:
            supplier_loc = env.ref(
                "stock.stock_location_suppliers", raise_if_not_found=False
            )
            if not supplier_loc:
                supplier_loc = (
                    env["stock.location"]
                    .sudo()
                    .search(
                        [
                            ("usage", "=", "supplier"),
                            ("company_id", "in", (company_id, False)),
                        ],
                        limit=1,
                    )
                )
            src_location_id = (
                supplier_loc.id
                if supplier_loc
                else picking_type.default_location_src_id.id
            )

        if not src_location_id:
            raise ValueError(ERR_SRC_LOCATION_NOT_CONFIGURED)

        # Destination internal stock location
        dest_location_id = picking_type.default_location_dest_id.id
        if not dest_location_id and picking_type.warehouse_id:
            dest_location_id = picking_type.warehouse_id.lot_stock_id.id
        if not dest_location_id:
            dest_location = (
                env["stock.location"]
                .sudo()
                .search(
                    [
                        ("usage", "=", "internal"),
                        ("company_id", "in", (company_id, False)),
                    ],
                    limit=1,
                )
            )
            dest_location_id = dest_location.id if dest_location else False

        if not dest_location_id:
            raise ValueError(ERR_DEST_LOCATION_NOT_CONFIGURED)

        return src_location_id, dest_location_id

    else:
        # Outbound: source internal stock location
        src_location_id = picking_type.default_location_src_id.id
        if not src_location_id and picking_type.warehouse_id:
            src_location_id = picking_type.warehouse_id.lot_stock_id.id
        if not src_location_id:
            src_location = (
                env["stock.location"]
                .sudo()
                .search(
                    [
                        ("usage", "=", "internal"),
                        ("company_id", "in", (company_id, False)),
                    ],
                    limit=1,
                )
            )
            src_location_id = src_location.id if src_location else False

        if not src_location_id:
            raise ValueError(ERR_SRC_LOCATION_NOT_CONFIGURED)

        # Destination customer location: prioritize partner.property_stock_customer
        dest_location_id = (
            partner.property_stock_customer.id
            if partner.property_stock_customer
            else False
        )
        if not dest_location_id:
            customer_loc = env.ref(
                "stock.stock_location_customers", raise_if_not_found=False
            )
            if not customer_loc:
                customer_loc = (
                    env["stock.location"]
                    .sudo()
                    .search(
                        [
                            ("usage", "=", "customer"),
                            ("company_id", "in", (company_id, False)),
                        ],
                        limit=1,
                    )
                )
            dest_location_id = (
                customer_loc.id
                if customer_loc
                else picking_type.default_location_dest_id.id
            )

        if not dest_location_id:
            raise ValueError(ERR_DEST_LOCATION_NOT_CONFIGURED)

        return src_location_id, dest_location_id


def parse_scheduled_date(date_str):
    """Parses date string supporting ISO 8601 or YYYY-MM-DD.

    Raises ValueError if format is invalid to prevent silent data corruption.
    """
    if not date_str:
        return fields.Datetime.now()

    clean_date = str(date_str).strip()
    if not clean_date:
        return fields.Datetime.now()

    try:
        if "T" in clean_date:
            normalized = clean_date.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        elif " " in clean_date:
            return datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S")
        else:
            parsed_d = datetime.strptime(clean_date, DATE_FMT_DATE_ONLY).date()
            return datetime.combine(parsed_d, time.min)
    except (ValueError, TypeError) as err:
        raise ValueError(
            f"Bad Request: Invalid date format '{date_str}'. Expected ISO-8601 or YYYY-MM-DD."
        ) from err


def validate_and_resolve_material_items(env, items):
    """Batch validates items and resolves products and units of measure.

    Uses strict AND domain matching for UoM category compatibility.
    """
    if not isinstance(items, list) or len(items) == 0:
        raise ValueError("Bad Request: Missing or empty 'items' array")

    product_obj = env["product.product"].sudo()
    uom_obj = env["uom.uom"].sudo()

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
    for idx, item in enumerate(items):
        code = str(item.get("sap_material_code")).strip()
        product = prod_map.get(code)
        if not product:
            raise ValueError(ERR_MATERIAL_NOT_FOUND.format(code=code))

        qty_raw = item.get("qty")
        if qty_raw is None:
            raise ValueError(
                f"Bad Request: Item #{idx + 1} ({code}) missing mandatory field 'qty'"
            )
        try:
            qty_val = float(qty_raw)
            if qty_val <= 0.0:
                raise ValueError(ERR_QTY_MUST_BE_POSITIVE)
        except (ValueError, TypeError) as qty_err:
            raise ValueError(
                f"Bad Request: Item #{idx + 1} ({code}) invalid 'qty': {qty_err}"
            ) from qty_err

        uom_str = item.get("uom")
        target_uom = product.uom_id
        if uom_str and isinstance(uom_str, str) and uom_str.strip():
            clean_uom = uom_str.strip()
            # Enforce AND domain to avoid mismatched UoM distortion
            found_uom = uom_obj.search(
                [
                    ("name", "=ilike", clean_uom),
                    ("category_id", "=", product.uom_id.category_id.id),
                ],
                limit=1,
            )
            if found_uom:
                target_uom = found_uom
            else:
                _logger.warning(
                    "UoM '%s' not found or incompatible for product '%s'. Falling back to '%s'",
                    clean_uom,
                    code,
                    product.uom_id.name,
                )

        validated_moves_data.append(
            {
                "product": product,
                "qty": qty_val,
                "uom": target_uom,
                "lot_name": item.get("lot_name"),
                "expiration_date": item.get("expiration_date"),
            }
        )

    return validated_moves_data
