# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sap_base_url = fields.Char(
        string="SAP Base URL",
        config_parameter="wms_sap_connector.sap_base_url",
        help="URL host server SAP / FastAPI simulator (misal: http://localhost:8000).",
    )
    sap_api_token = fields.Char(
        string="SAP API Token",
        config_parameter="wms_sap_connector.sap_api_token",
        help="Token rahasia otentikasi untuk otorisasi webhook dari Odoo ke SAP.",
    )
