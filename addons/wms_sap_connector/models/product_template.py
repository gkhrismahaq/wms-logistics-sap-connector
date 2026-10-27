"""Extension of product.template for SAP integration."""

from odoo import fields, models

from ..constants import ERR_DUPLICATE_MATERIAL_CODE


class ProductTemplate(models.Model):
    _inherit = "product.template"

    sap_material_code = fields.Char(
        string="SAP Material Code",
        index=True,
        copy=False,
        help="Unique SKU identifier in SAP system",
    )

    _sql_constraints = [
        (
            "sap_material_code_unique",
            "UNIQUE(sap_material_code)",
            ERR_DUPLICATE_MATERIAL_CODE,
        )
    ]
