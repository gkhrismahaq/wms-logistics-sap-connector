"""SAP Synchronization Audit Log Model."""

import json
import uuid
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..constants import (
    ALLOWED_SYNC_TYPES,
    DIRECTION_INBOUND,
    DIRECTION_OUTBOUND,
    ERR_ONLY_MANAGER_CAN_RETRY_SYNC,
    GROUP_WMS_MANAGER,
    REF_PREFIX_MASTER_DATA,
    SAP_DIRECTION_SELECTION,
    SAP_SYNC_LOG_STATUS_SELECTION,
    SAP_SYNC_TYPE_SELECTION,
    SYNC_STATUS_FAILED,
    SYNC_STATUS_PENDING,
    SYNC_STATUS_SUCCESS,
    SYNC_STATUS_SYNCED,
    SYNC_TYPE_INBOUND_PO,
    SYNC_TYPE_OUTBOUND_SO,
)


class SapSyncLog(models.Model):
    _name = "sap.sync.log"
    _description = "SAP Synchronization Audit Log"
    _order = "sync_date desc, id desc"

    name = fields.Char(
        string="Transaction Reference",
        required=True,
        copy=False,
        index=True,
        help="Unique synchronization transaction reference.",
    )
    sync_type = fields.Selection(
        selection=SAP_SYNC_TYPE_SELECTION,
        string="Sync Type",
        required=True,
        index=True,
        help="Type of synchronized business data.",
    )
    direction = fields.Selection(
        selection=SAP_DIRECTION_SELECTION,
        string="Direction",
        required=True,
        index=True,
        help="Direction of data flow between SAP and Odoo.",
    )
    payload = fields.Text(
        string="Payload (JSON)",
        help="Complete raw JSON request payload content.",
    )
    response_payload = fields.Text(
        string="Response Payload (JSON)",
        help="Complete raw JSON response received from external system.",
    )
    status = fields.Selection(
        selection=SAP_SYNC_LOG_STATUS_SELECTION,
        string="Status",
        default=SYNC_STATUS_PENDING,
        required=True,
        index=True,
        help="Transaction execution result status.",
    )
    error_message = fields.Text(
        string="Error Message",
        help="Technical error details if execution fails.",
    )
    sync_date = fields.Datetime(
        string="Sync Date",
        default=fields.Datetime.now,
        required=True,
        index=True,
        help="Timestamp of synchronization recording.",
    )

    @api.model
    def generate_sync_ref(self, prefix=REF_PREFIX_MASTER_DATA):
        """Generates unique transaction reference: SYNC-{prefix}-YYYYMMDD-XXXXXX."""
        date_str = datetime.now().strftime("%Y%m%d")
        short_id = uuid.uuid4().hex[:6].upper()
        return f"SYNC-{prefix}-{date_str}-{short_id}"

    @api.constrains("sync_type")
    def _check_sync_type(self):
        for record in self:
            if record.sync_type not in ALLOWED_SYNC_TYPES:
                raise ValidationError(
                    _(
                        "Invalid sync_type '%(sync_type)s'. Must be one of %(allowed)s",
                        sync_type=record.sync_type,
                        allowed=list(ALLOWED_SYNC_TYPES),
                    )
                )

    def action_retry_sync(self):
        """Triggers actual retry of failed synchronization transactions."""
        if not (
            self.env.user.has_group(GROUP_WMS_MANAGER)
            or self.env.is_superuser()
        ):
            raise AccessError(_(ERR_ONLY_MANAGER_CAN_RETRY_SYNC))

        for record in self:
            if record.status != SYNC_STATUS_FAILED:
                raise UserError(
                    _("Only transactions with 'Failed' status can be retried.")
                )

            if record.direction == DIRECTION_OUTBOUND:
                picking = False
                if record.payload:
                    try:
                        p_data = json.loads(record.payload)
                        sap_doc = p_data.get("sap_doc_number")
                        if sap_doc:
                            picking = self.env["stock.picking"].search(
                                [("sap_doc_number", "=", sap_doc)], limit=1
                            )
                    except (ValueError, TypeError):
                        pass

                if picking:
                    if record.sync_type == SYNC_TYPE_INBOUND_PO:
                        picking._send_sap_goods_receipt_webhook()
                    elif record.sync_type == SYNC_TYPE_OUTBOUND_SO:
                        picking._send_sap_goods_issue_webhook()

                    is_synced = picking.sap_sync_status == SYNC_STATUS_SYNCED
                    record.write(
                        {
                            "status": (
                                SYNC_STATUS_SUCCESS if is_synced else SYNC_STATUS_FAILED
                            ),
                            "error_message": (
                                False
                                if is_synced
                                else _("Retry outbound webhook transmission failed.")
                            ),
                        }
                    )
                else:
                    record.write(
                        {
                            "status": SYNC_STATUS_PENDING,
                            "error_message": False,
                        }
                    )
            elif record.direction == DIRECTION_INBOUND:
                success = False
                err_msg = None
                if record.payload:
                    try:
                        p_data = json.loads(record.payload)
                        if record.sync_type == SYNC_TYPE_INBOUND_PO:
                            self.env["stock.picking"].create_inbound_from_sap(p_data)
                            success = True
                        elif record.sync_type == SYNC_TYPE_OUTBOUND_SO:
                            self.env["stock.picking"].create_outbound_from_sap(p_data)
                            success = True
                    except Exception as exc:  # noqa: BLE001
                        err_msg = str(exc)

                if success:
                    record.write(
                        {
                            "status": SYNC_STATUS_SUCCESS,
                            "error_message": False,
                        }
                    )
                else:
                    record.write(
                        {
                            "status": SYNC_STATUS_FAILED,
                            "error_message": err_msg
                            or _("Retry inbound processing failed."),
                        }
                    )
        return True
