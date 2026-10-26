# -*- coding: utf-8 -*-
from odoo import fields, models
from ..constants import (
    CONFIG_PARAM_SAP_API_TOKEN,
    CONFIG_PARAM_SAP_BASE_URL,
)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sap_base_url = fields.Char(
        string="SAP Base URL",
        config_parameter=CONFIG_PARAM_SAP_BASE_URL,
        help="SAP Upper Line / API gateway host URL (e.g. http://localhost:8000).",
    )
    sap_api_token = fields.Char(
        string="SAP API Token",
        config_parameter=CONFIG_PARAM_SAP_API_TOKEN,
        help="Secret API token used for inbound and outbound webhook authentication.",
    )
