"""Extension of res.partner for SAP integration."""

from odoo import fields, models

from ..constants import ERR_DUPLICATE_PARTNER_CODE


class ResPartner(models.Model):
    _inherit = "res.partner"

    sap_partner_code = fields.Char(
        string="SAP Partner Code",
        index=True,
        copy=False,
        help="Unique Partner/Vendor/Customer identifier in SAP system",
    )

    _sql_constraints = [
        (
            "sap_partner_code_unique",
            "UNIQUE(sap_partner_code)",
            ERR_DUPLICATE_PARTNER_CODE,
        )
    ]
