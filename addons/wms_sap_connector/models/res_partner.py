from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    sap_partner_code = fields.Char(
        string="SAP Partner Code",
        index=True,
        copy=False,
        help="Unique Partner/Vendor/Customer identifier in SAP system",
    )
