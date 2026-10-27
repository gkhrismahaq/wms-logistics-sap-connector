"""WMS Vehicle Model for Fleet Management."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..constants import (
    DEFAULT_VEHICLE_CAPACITY,
    ERR_DUPLICATE_LICENSE_PLATE,
    FLOAT_DIGITS_CAPACITY,
    FLOAT_DIGITS_VOLUME,
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
        help="Vehicle license plate number for logistics fleet (e.g. 'B 1234 WMS')",
    )
    driver_id = fields.Many2one(
        "res.partner",
        string="Assigned Driver",
        domain=[("is_company", "=", False)],
        ondelete="set null",
        help="Default designated courier or driver responsible for this vehicle",
    )
    max_weight = fields.Float(
        string="Max Weight Capacity (kg)",
        digits=FLOAT_DIGITS_CAPACITY,
        default=DEFAULT_VEHICLE_CAPACITY,
        help="Maximum cargo payload weight capacity in kilograms (kg)",
    )
    max_volume = fields.Float(
        string="Max Volume Capacity (m³)",
        digits=FLOAT_DIGITS_VOLUME,
        default=DEFAULT_VEHICLE_CAPACITY,
        help="Maximum cargo volumetric capacity in cubic meters (m³)",
    )
    state = fields.Selection(
        selection=VEHICLE_STATE_SELECTION,
        string="Status",
        default=VEHICLE_STATE_AVAILABLE,
        required=True,
        help="Operational state of logistics vehicle",
    )

    _sql_constraints = [
        (
            "license_plate_unique",
            "unique(license_plate)",
            ERR_DUPLICATE_LICENSE_PLATE,
        ),
    ]

    @api.constrains("max_weight", "max_volume")
    def _check_capacities(self):
        """Validates that cargo capacities are non-negative."""
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
        """Normalizes license plate to uppercase and stripped before creation."""
        for vals in vals_list:
            if vals.get("license_plate"):
                vals["license_plate"] = vals["license_plate"].strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        """Normalizes license plate to uppercase and stripped before update."""
        if vals.get("license_plate"):
            vals["license_plate"] = vals["license_plate"].strip().upper()
        return super().write(vals)
