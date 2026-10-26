# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from ..constants import (
    ALLOWED_SYNC_TYPES,
    SAP_DIRECTION_SELECTION,
    SAP_SYNC_LOG_STATUS_SELECTION,
    SAP_SYNC_TYPE_SELECTION,
    SYNC_STATUS_FAILED,
    SYNC_STATUS_PENDING,
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
        help="Complete raw JSON payload content.",
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
        """Triggers retry of failed synchronization transactions."""
        for record in self:
            if record.status != SYNC_STATUS_FAILED:
                raise UserError(
                    _("Only transactions with 'Failed' status can be retried.")
                )
            record.write(
                {
                    "status": SYNC_STATUS_PENDING,
                    "error_message": False,
                }
            )
        return True
