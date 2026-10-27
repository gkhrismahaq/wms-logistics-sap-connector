"""Extension of res.config.settings for SAP integration."""

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
        help=(
            "SAP Upper Line / API gateway URL "
            "(e.g. http://mock-sap:8000 for Docker network, or external SAP endpoint)."
        ),
    )
    sap_api_token = fields.Char(
        string="SAP API Token",
        config_parameter=CONFIG_PARAM_SAP_API_TOKEN,
        help="Secret API token used for inbound and outbound webhook authentication.",
    )
