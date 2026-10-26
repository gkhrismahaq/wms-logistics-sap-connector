from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    sap_plant_code = fields.Char(
        string="SAP Plant Code",
        size=4,
        index=True,
        help="SAP Plant / Facility code governing this storage facility (e.g. 1000)",
    )
    sap_sloc_code = fields.Char(
        string="SAP Storage Location",
        size=4,
        index=True,
        help="SAP Storage Location code (e.g. SL01, 1001)",
    )
    barcode = fields.Char(
        string="Barcode",
        index=True,
        copy=False,
        help="Physical barcode attached to the aisle, rack, or bin for scanner operations",
    )
