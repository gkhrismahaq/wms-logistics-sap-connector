# -*- coding: utf-8 -*-
"""WMS Vehicle Model for Fleet Management.

Provides the wms.vehicle model to track logistics transport vehicles,
carrying weight/volume capacities, assigned drivers, and operational states.
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..constants import (
    VEHICLE_STATE_AVAILABLE,
    VEHICLE_STATE_SELECTION,
)


class WmsVehicle(models.Model):
    _name = "wms.vehicle"
    _description = "WMS Logistics Vehicle"
    _rec_name = "license_plate"
    _order = "license_plate asc"

    license_plate = fields.Char(
        string="License Plate",
        required=True,
        index=True,
        copy=False,
        help="Nomor plat polisi kendaraan armada logistik (contoh: 'B 1234 WMS')",
    )
    driver_id = fields.Many2one(
        "res.partner",
        string="Assigned Driver",
        domain=[("is_company", "=", False)],
        ondelete="set null",
        help="Supir tetap penanggung jawab armada kendaraan",
    )
    max_weight = fields.Float(
        string="Max Weight Capacity (kg)",
        digits=(12, 2),
        default=0.0,
        help="Kapasitas muatan berat maksimum kargo dalam satuan kilogram (kg)",
    )
    max_volume = fields.Float(
        string="Max Volume Capacity (m³)",
        digits=(12, 2),
        default=0.0,
        help="Kapasitas volume kubikasi kargo maksimum dalam satuan meter kubik (m³)",
    )
    state = fields.Selection(
        selection=VEHICLE_STATE_SELECTION,
        string="Status",
        default=VEHICLE_STATE_AVAILABLE,
        required=True,
        help="Kondisi operasional armada logistik",
    )

    _sql_constraints = [
        (
            "license_plate_unique",
            "unique(license_plate)",
            "Nomor plat polisi kendaraan harus unik!",
        ),
    ]

    @api.constrains("max_weight", "max_volume")
    def _check_capacities(self):
        """Validate that cargo capacities are non-negative."""
        for record in self:
            if record.max_weight < 0:
                raise ValidationError(
                    _("Kapasitas muatan berat maksimum tidak boleh bernilai negatif!")
                )
            if record.max_volume < 0:
                raise ValidationError(
                    _("Kapasitas volume kubikasi kargo tidak boleh bernilai negatif!")
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Normalize license plate to uppercase and stripped before creation."""
        for vals in vals_list:
            if vals.get("license_plate"):
                vals["license_plate"] = vals["license_plate"].strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        """Normalize license plate to uppercase and stripped before update."""
        if vals.get("license_plate"):
            vals["license_plate"] = vals["license_plate"].strip().upper()
        return super().write(vals)
