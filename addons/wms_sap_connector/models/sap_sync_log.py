# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class SapSyncLog(models.Model):
    _name = "sap.sync.log"
    _description = "SAP Synchronization Audit Log"
    _order = "sync_date desc, id desc"

    name = fields.Char(
        string="Transaction Reference",
        required=True,
        copy=False,
        index=True,
        help="Nomor referensi unik transaksi sinkronisasi.",
    )
    sync_type = fields.Selection(
        [
            ("master_product", "Master Product / Material"),
            ("master_partner", "Master Partner / Vendor / Customer"),
            ("inbound_po", "Inbound Purchase Order"),
            ("outbound_so", "Outbound Sales Delivery"),
        ],
        string="Sync Type",
        required=True,
        index=True,
        help="Jenis data integrasi.",
    )
    direction = fields.Selection(
        [
            ("inbound", "Inbound (SAP -> Odoo)"),
            ("outbound", "Outbound (Odoo -> SAP)"),
        ],
        string="Direction",
        required=True,
        index=True,
        help="Arah aliran data.",
    )
    payload = fields.Text(
        string="Payload (JSON)",
        help="Salinan lengkap struktur payload JSON yang dipertukarkan.",
    )
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        string="Status",
        default="pending",
        required=True,
        index=True,
        help="Hasil eksekusi transaksi.",
    )
    error_message = fields.Text(
        string="Error Message",
        help="Rekaman pesan kegagalan teknis jika transaksi mengalami galat.",
    )
    sync_date = fields.Datetime(
        string="Sync Date",
        default=fields.Datetime.now,
        required=True,
        index=True,
        help="Waktu pencatatan log integrasi.",
    )

    def action_retry_sync(self):
        """Memicu pengiriman ulang transaksi yang berstatus failed.

        Hanya record dengan status 'failed' yang diizinkan untuk diproses ulang.
        Jika record memiliki status selain 'failed', sistem membangkitkan UserError.
        """
        for record in self:
            if record.status != "failed":
                raise UserError(
                    _(
                        "Hanya transaksi dengan status 'Failed' yang dapat dikirim ulang."
                    )
                )
            record.write(
                {
                    "status": "pending",
                    "error_message": False,
                }
            )
        return True
