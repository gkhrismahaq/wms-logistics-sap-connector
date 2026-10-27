"""Extension of stock.picking for WMS Logistics SAP Integration."""

import logging

import odoo
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare

from ..constants import (
    ERR_CANNOT_DELETE_DONE_PICKING,
    ERR_CANNOT_DELETE_SAP_PICKING,
    ERR_DUPLICATE_SAP_DOC_NUMBER,
    ERR_ONLY_DISPATCHER_CAN_ASSIGN_FLEET,
    ERR_ONLY_DISPATCHER_CAN_MANAGE_POD,
    ERR_ONLY_MANAGER_CAN_DELETE_PICKING,
    FLOAT_DIGITS_CAPACITY,
    FLOAT_DIGITS_VOLUME,
    GROUP_WMS_DISPATCHER,
    GROUP_WMS_MANAGER,
    PICKING_STATE_ASSIGNED,
    PICKING_STATE_CANCEL,
    PICKING_STATE_CONFIRMED,
    PICKING_STATE_DONE,
    PICKING_TYPE_CODE_INCOMING,
    PICKING_TYPE_CODE_OUTGOING,
    SAP_PICKING_SYNC_STATUS_SELECTION,
    SYNC_STATUS_DRAFT,
    SYNC_STATUS_FAILED,
    SYNC_STATUS_SYNCED,
    VEHICLE_STATE_AVAILABLE,
    VEHICLE_STATE_MAINTENANCE,
    VEHICLE_STATE_ON_DELIVERY,
)
from ..services import (
    sap_inbound_service,
    sap_outbound_service,
    sap_webhook_service,
)

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    sap_doc_number = fields.Char(
        string="SAP Document Number",
        index=True,
        copy=False,
        help=(
            "Original SAP purchase order or delivery document reference "
            "(e.g. PO-SAP-2026-001)."
        ),
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
        domain=f"[('state', '!=', '{VEHICLE_STATE_MAINTENANCE}')]",
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
        digits=FLOAT_DIGITS_CAPACITY,
        help="Aggregated total weight in kilograms computed from all active stock moves.",
    )
    total_volume = fields.Float(
        string="Total Volume (m³)",
        compute="_compute_total_weight_volume",
        store=True,
        digits=FLOAT_DIGITS_VOLUME,
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
    is_dispatcher_or_manager = fields.Boolean(
        string="Is Dispatcher or Manager",
        compute="_compute_is_dispatcher_or_manager",
        search=False,
    )

    _sql_constraints = [
        (
            "sap_doc_number_company_uniq",
            "unique(sap_doc_number, company_id)",
            ERR_DUPLICATE_SAP_DOC_NUMBER,
        ),
    ]

    def _compute_is_dispatcher_or_manager(self):
        is_dm = (
            self.env.user.has_group(GROUP_WMS_DISPATCHER)
            or self.env.user.has_group(GROUP_WMS_MANAGER)
            or self.env.user.has_group("base.group_system")
            or self.env.user.id == odoo.SUPERUSER_ID
        )
        for picking in self:
            picking.is_dispatcher_or_manager = is_dm

    @api.depends("proof_of_delivery", "pod_signed_by")
    def _compute_has_pod(self):
        """Computes whether physical proof of delivery exists."""
        for picking in self:
            picking.has_pod = bool(picking.proof_of_delivery or picking.pod_signed_by)

    @api.onchange("proof_of_delivery", "pod_signed_by")
    def _onchange_pod_fields(self):
        """Auto-populates pod_timestamp when proof or receiver is recorded."""
        if (self.proof_of_delivery or self.pod_signed_by) and not self.pod_timestamp:
            self.pod_timestamp = fields.Datetime.now()

    @api.model_create_multi
    def create(self, vals_list):
        """Overrides create to enforce security assignment limits and pod_timestamp."""
        is_dm = (
            self.env.user.has_group(GROUP_WMS_DISPATCHER)
            or self.env.user.has_group(GROUP_WMS_MANAGER)
            or self.env.user.has_group("base.group_system")
            or self.env.user.id == odoo.SUPERUSER_ID
        )
        for vals in vals_list:
            if ("vehicle_id" in vals or "driver_id" in vals) and not is_dm:
                raise AccessError(_(ERR_ONLY_DISPATCHER_CAN_ASSIGN_FLEET))
            if (
                any(
                    f in vals
                    for f in ("proof_of_delivery", "pod_signed_by", "pod_timestamp")
                )
                and not is_dm
            ):
                raise AccessError(_(ERR_ONLY_DISPATCHER_CAN_MANAGE_POD))
            if (
                vals.get("proof_of_delivery") or vals.get("pod_signed_by")
            ) and not vals.get("pod_timestamp"):
                vals["pod_timestamp"] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        """Overrides write safely enforcing role limits without in-place mutation."""
        is_dm = (
            self.env.user.has_group(GROUP_WMS_DISPATCHER)
            or self.env.user.has_group(GROUP_WMS_MANAGER)
            or self.env.user.has_group("base.group_system")
            or self.env.user.id == odoo.SUPERUSER_ID
        )
        if ("vehicle_id" in vals or "driver_id" in vals) and not is_dm:
            raise AccessError(_(ERR_ONLY_DISPATCHER_CAN_ASSIGN_FLEET))
        if (
            any(
                f in vals
                for f in ("proof_of_delivery", "pod_signed_by", "pod_timestamp")
            )
            and not is_dm
        ):
            raise AccessError(_(ERR_ONLY_DISPATCHER_CAN_MANAGE_POD))

        # Non-destructive batch write handling for missing pod_timestamp
        if (
            any(f in vals for f in ("proof_of_delivery", "pod_signed_by"))
            and "pod_timestamp" not in vals
        ):
            pickings_to_stamp = self.filtered(lambda p: not p.pod_timestamp)
            if pickings_to_stamp:
                super(StockPicking, pickings_to_stamp).write(
                    {"pod_timestamp": fields.Datetime.now()}
                )

        res = super().write(vals)

        # Vehicle state transition to ON_DELIVERY when assigned
        for picking in self:
            if (
                picking.vehicle_id
                and picking.state == PICKING_STATE_ASSIGNED
                and picking.picking_type_id.code == PICKING_TYPE_CODE_OUTGOING
                and picking.vehicle_id.state == VEHICLE_STATE_AVAILABLE
            ):
                picking.vehicle_id.write({"state": VEHICLE_STATE_ON_DELIVERY})

        # Trigger outbound Goods Issue webhook on late POD upload
        if any(f in vals for f in ("proof_of_delivery", "pod_signed_by")):
            for picking in self:
                if (
                    picking.picking_type_id.code == PICKING_TYPE_CODE_OUTGOING
                    and picking.state == PICKING_STATE_DONE
                    and picking.sap_doc_number
                    and picking.has_pod
                    and picking.sap_sync_status != SYNC_STATUS_SYNCED
                ):
                    picking._send_sap_goods_issue_webhook()

        return res

    def unlink(self):
        """Prevents unauthorized deletion of logistics transfers.

        Enforces enterprise-grade data integrity:
        1. Non-managers are strictly forbidden from deleting transfer pickings.
        2. Pickings integrated with SAP (carrying sap_doc_number) cannot be deleted.
        3. Completed (done) transfers cannot be deleted under any circumstances.
        """
        is_manager = (
            self.env.user.has_group(GROUP_WMS_MANAGER)
            or self.env.user.has_group("base.group_system")
            or self.env.user.id == odoo.SUPERUSER_ID
        )
        for picking in self:
            if picking.sap_doc_number:
                raise UserError(
                    _(ERR_CANNOT_DELETE_SAP_PICKING) % picking.sap_doc_number
                )
            if picking.state == PICKING_STATE_DONE:
                raise UserError(_(ERR_CANNOT_DELETE_DONE_PICKING))
            if not is_manager:
                raise AccessError(_(ERR_ONLY_MANAGER_CAN_DELETE_PICKING))
        return super().unlink()

    def action_cancel(self):
        """Overrides action_cancel to release vehicle and free sap_doc_number constraint."""
        res = super().action_cancel()
        for picking in self:
            if picking.vehicle_id:
                active_count = self.search_count(
                    [
                        ("id", "!=", picking.id),
                        ("vehicle_id", "=", picking.vehicle_id.id),
                        (
                            "state",
                            "in",
                            (PICKING_STATE_CONFIRMED, PICKING_STATE_ASSIGNED),
                        ),
                    ]
                )
                if active_count == 0:
                    picking.vehicle_id.write({"state": VEHICLE_STATE_AVAILABLE})

            if picking.sap_doc_number and not picking.sap_doc_number.endswith(
                "-CANCEL"
            ):
                picking.sudo().write(
                    {
                        "sap_doc_number": (
                            f"{picking.sap_doc_number}-CANCEL-{picking.id}"
                        )
                    }
                )
        return res

    @api.onchange("vehicle_id")
    def _onchange_vehicle_id(self):
        """Auto-populates driver from assigned vehicle default driver."""
        if self.vehicle_id and self.vehicle_id.driver_id:
            self.driver_id = self.vehicle_id.driver_id

    @api.depends(
        "move_ids.product_uom_qty",
        "move_ids.product_uom",
        "move_ids.product_id.weight",
        "move_ids.product_id.volume",
        "move_ids.state",
    )
    def _compute_total_weight_volume(self):
        """Computes accumulated weight and volume converting move UoM to product reference UoM."""
        for picking in self:
            weight = 0.0
            volume = 0.0
            for move in picking.move_ids.filtered(
                lambda m: m.state != PICKING_STATE_CANCEL
            ):
                prod = move.product_id
                if prod:
                    # Convert move UoM quantity to product reference UoM quantity
                    move_qty = move.product_uom_qty or 0.0
                    qty_in_prod_uom = (
                        move.product_uom._compute_quantity(move_qty, prod.uom_id)
                        if move.product_uom and prod.uom_id
                        else move_qty
                    )
                    weight += (prod.weight or 0.0) * qty_in_prod_uom
                    volume += (prod.volume or 0.0) * qty_in_prod_uom
            picking.total_weight = weight
            picking.total_volume = volume

    @api.constrains("vehicle_id", "total_weight", "total_volume")
    def _check_vehicle_capacity(self):
        """Enforces vehicle cargo capacity limits using precision float comparison."""
        for picking in self:
            if not picking.vehicle_id:
                continue
            v = picking.vehicle_id
            if (
                v.max_weight > 0.0
                and float_compare(
                    picking.total_weight, v.max_weight, precision_digits=2
                )
                > 0
            ):
                raise ValidationError(
                    f"Overcapacity Error: Total weight ({picking.total_weight:.2f} kg) "
                    f"exceeds vehicle maximum weight capacity ({v.max_weight:.2f} kg) "
                    f"for vehicle '{v.license_plate}'."
                )
            if (
                v.max_volume > 0.0
                and float_compare(
                    picking.total_volume, v.max_volume, precision_digits=4
                )
                > 0
            ):
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

    def _generate_sync_ref(self, prefix):
        """Delegates to centralized reference generator on sap.sync.log."""
        return self.env["sap.sync.log"].generate_sync_ref(prefix)

    def _send_sap_goods_receipt_webhook(self):
        """Delegates Goods Receipt webhook dispatch to dedicated service."""
        for picking in self:
            sap_webhook_service.send_goods_receipt_webhook(picking)

    def action_send_sap_goods_receipt_webhook(self):
        """Action button to manually trigger or retry Goods Receipt webhook transmission."""
        self.ensure_one()
        self._send_sap_goods_receipt_webhook()
        return True

    def _send_sap_goods_issue_webhook(self):
        """Delegates Goods Issue webhook dispatch to dedicated service."""
        for picking in self:
            sap_webhook_service.send_goods_issue_webhook(picking)

    def action_send_sap_goods_issue_webhook(self):
        """Action button to manually trigger or retry Goods Issue webhook transmission."""
        self.ensure_one()
        self._send_sap_goods_issue_webhook()
        return True

    def _action_done(self):
        """Overrides _action_done to trigger webhooks and release vehicle availability."""
        res = super()._action_done()
        for picking in self:
            if picking.vehicle_id:
                active_count = self.search_count(
                    [
                        ("id", "!=", picking.id),
                        ("vehicle_id", "=", picking.vehicle_id.id),
                        (
                            "state",
                            "in",
                            (PICKING_STATE_CONFIRMED, PICKING_STATE_ASSIGNED),
                        ),
                    ]
                )
                if active_count == 0:
                    picking.vehicle_id.write({"state": VEHICLE_STATE_AVAILABLE})

            if (
                picking.picking_type_id.code == PICKING_TYPE_CODE_INCOMING
                and picking.sap_doc_number
                and picking.sap_sync_status != SYNC_STATUS_SYNCED
            ):
                picking._send_sap_goods_receipt_webhook()
            elif (
                picking.picking_type_id.code == PICKING_TYPE_CODE_OUTGOING
                and picking.sap_doc_number
                and picking.has_pod
                and picking.sap_sync_status != SYNC_STATUS_SYNCED
            ):
                picking._send_sap_goods_issue_webhook()
        return res

    @api.model
    def create_inbound_from_sap(self, payload_dict):
        """Delegates inbound PO processing to dedicated inbound service."""
        return sap_inbound_service.process_inbound_po(self, payload_dict)

    @api.model
    def create_outbound_from_sap(self, payload_dict):
        """Delegates outbound delivery processing to dedicated outbound service."""
        return sap_outbound_service.process_outbound_delivery(self, payload_dict)
