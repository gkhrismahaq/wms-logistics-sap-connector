# -*- coding: utf-8 -*-
{
    "name": "WMS Logistics SAP Connector",
    "version": "17.0.1.0.0",
    "category": "Inventory/Logistics",
    "summary": "Odoo 17 Two-Tier WMS & Logistics Execution System integrated with SAP Upper Line",
    "author": "Gilang Khrismahaq",
    "website": "https://github.com/gkhrismahaq/wms-logistics-sap-connector",
    "license": "LGPL-3",
    "depends": [
        "base",
        "stock",
        "delivery",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/sap_sync_log_views.xml",
        "views/res_config_settings_views.xml",
        "views/product_template_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
