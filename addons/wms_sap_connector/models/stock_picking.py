# -*- coding: utf-8 -*-
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    sap_doc_number = fields.Char(
        string="SAP Document Number",
        index=True,
        copy=False,
        help="Nomor referensi dokumen pesanan pembelian atau pengiriman asal di SAP (misal: PO-SAP-2026-001).",
    )
    sap_sync_status = fields.Selection(
        [
            ("draft", "Draft / Not Synced"),
            ("pending", "Pending Sync"),
            ("synced", "Synced to SAP"),
            ("failed", "Sync Failed"),
        ],
        string="SAP Sync Status",
        default="draft",
        index=True,
        copy=False,
        help="Status siklus hidup sinkronisasi dokumen transaksi dengan SAP.",
    )

    def action_mark_synced(self):
        """Marks picking record as synced to SAP."""
        return self.write({"sap_sync_status": "synced"})

    def action_mark_failed(self):
        """Marks picking record as sync failed."""
        return self.write({"sap_sync_status": "failed"})
