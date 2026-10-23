# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    sap_material_code = fields.Char(
        string="SAP Material Code",
        index=True,
        copy=False,
        help="Unique SKU identifier in SAP system",
    )
