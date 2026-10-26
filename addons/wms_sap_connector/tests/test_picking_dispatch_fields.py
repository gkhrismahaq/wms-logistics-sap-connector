from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

from ..constants import (
    PICKING_TYPE_CODE_OUTGOING,
    VEHICLE_STATE_AVAILABLE,
)


@tagged("post_install", "-at_install", "wms_sap")
class TestPickingDispatchFields(TransactionCase):
    """Test suite for Stock Picking Dispatch Fields, Volume/Weight Computation, and Vehicle Capacity."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.driver_1 = cls.env["res.partner"].create(
            {
                "name": "Budi Santoso",
                "is_company": False,
            }
        )
        cls.driver_2 = cls.env["res.partner"].create(
            {
                "name": "Ahmad Hidayat",
                "is_company": False,
            }
        )

        cls.vehicle_standard = cls.env["wms.vehicle"].create(
            {
                "license_plate": "B 1234 DISP",
                "driver_id": cls.driver_1.id,
                "max_weight": 500.0,
                "max_volume": 5.0,
                "state": VEHICLE_STATE_AVAILABLE,
            }
        )

        cls.vehicle_unlimited = cls.env["wms.vehicle"].create(
            {
                "license_plate": "B 9999 DISP",
                "driver_id": False,
                "max_weight": 0.0,
                "max_volume": 0.0,
                "state": VEHICLE_STATE_AVAILABLE,
            }
        )

        cls.product_kopi = cls.env["product.product"].create(
            {
                "name": "Kopi Sachet 500g",
                "sap_material_code": "MAT-KOPI-DISP",
                "type": "product",
                "weight": 0.5,
                "volume": 0.02,
            }
        )

        cls.product_teh = cls.env["product.product"].create(
            {
                "name": "Teh Celup Kotak 250g",
                "sap_material_code": "MAT-TEH-DISP",
                "type": "product",
                "weight": 0.25,
                "volume": 0.01,
            }
        )

        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Toko Retail Makmur",
                "customer_rank": 1,
            }
        )

        cls.picking_type_out = cls.env["stock.picking.type"].search(
            [("code", "=", PICKING_TYPE_CODE_OUTGOING)], limit=1
        )
        cls.src_loc = cls.picking_type_out.default_location_src_id
        cls.dest_loc = cls.customer.property_stock_customer

    def _create_outgoing_picking(self, items):
        """Helper to create an outgoing picking with moves."""
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "partner_id": self.customer.id,
                "location_id": self.src_loc.id,
                "location_dest_id": self.dest_loc.id,
                "origin": "TEST-DISPATCH-01",
            }
        )
        for prod, qty in items:
            self.env["stock.move"].create(
                {
                    "name": prod.name,
                    "product_id": prod.id,
                    "product_uom_qty": qty,
                    "product_uom": prod.uom_id.id,
                    "picking_id": picking.id,
                    "location_id": self.src_loc.id,
                    "location_dest_id": self.dest_loc.id,
                }
            )
        picking.action_confirm()
        return picking

    def test_01_onchange_vehicle_auto_populates_driver(self):
        """Selecting a vehicle with a driver must auto-populate the driver on picking."""
        picking = self.env["stock.picking"].new(
            {
                "picking_type_id": self.picking_type_out.id,
                "partner_id": self.customer.id,
            }
        )
        picking.vehicle_id = self.vehicle_standard
        picking._onchange_vehicle_id()
        self.assertEqual(picking.driver_id, self.driver_1)

        # Dispatcher manual override of driver
        picking.driver_id = self.driver_2
        self.assertEqual(picking.driver_id, self.driver_2)

    def test_02_compute_total_weight_and_volume(self):
        """Aggregated total_weight and total_volume must reflect sum of moves products."""
        # 100 kopi * 0.5kg = 50kg, 100 kopi * 0.02m3 = 2.0m3
        # 200 teh * 0.25kg = 50kg, 200 teh * 0.01m3 = 2.0m3
        # Total expected: 100.0 kg, 4.0 m3
        picking = self._create_outgoing_picking(
            [(self.product_kopi, 100.0), (self.product_teh, 200.0)]
        )
        self.assertAlmostEqual(picking.total_weight, 100.0, places=2)
        self.assertAlmostEqual(picking.total_volume, 4.0, places=4)

        # Cancel one move and verify recalculation
        move_to_cancel = picking.move_ids.filtered(
            lambda m: m.product_id == self.product_teh
        )
        move_to_cancel._action_cancel()
        picking._compute_total_weight_volume()
        self.assertAlmostEqual(picking.total_weight, 50.0, places=2)
        self.assertAlmostEqual(picking.total_volume, 2.0, places=4)

    def test_03_vehicle_capacity_validation_success(self):
        """Assigning vehicle within capacity limits must succeed without error."""
        # 100kg, 4.0m3 vs Vehicle max_weight=500kg, max_volume=5.0m3
        picking = self._create_outgoing_picking(
            [(self.product_kopi, 100.0), (self.product_teh, 200.0)]
        )
        picking.write(
            {
                "vehicle_id": self.vehicle_standard.id,
                "driver_id": self.driver_1.id,
            }
        )
        self.assertEqual(picking.vehicle_id, self.vehicle_standard)
        self.assertEqual(picking.driver_id, self.driver_1)

    def test_04_vehicle_capacity_overweight_constraint(self):
        """Assigning vehicle where total_weight exceeds max_weight must raise ValidationError."""
        # 1200 kopi * 0.5kg = 600kg > Vehicle max_weight=500kg
        picking = self._create_outgoing_picking([(self.product_kopi, 1200.0)])
        self.assertAlmostEqual(picking.total_weight, 600.0, places=2)

        with self.assertRaises(ValidationError) as err:
            picking.write({"vehicle_id": self.vehicle_standard.id})
        self.assertIn("Overcapacity Error: Total weight", str(err.exception))
        self.assertIn("exceeds vehicle maximum weight capacity", str(err.exception))

    def test_05_vehicle_capacity_overvolume_constraint(self):
        """Assigning vehicle where total_volume exceeds max_volume must raise ValidationError."""
        # Create small weight but small volume vehicle
        vehicle_small_vol = self.env["wms.vehicle"].create(
            {
                "license_plate": "B 5555 VOL",
                "max_weight": 2000.0,
                "max_volume": 2.0,
                "state": VEHICLE_STATE_AVAILABLE,
            }
        )
        # 200 kopi * 0.02m3 = 4.0m3 > 2.0m3
        picking = self._create_outgoing_picking([(self.product_kopi, 200.0)])
        self.assertAlmostEqual(picking.total_volume, 4.0, places=4)

        with self.assertRaises(ValidationError) as err:
            picking.write({"vehicle_id": vehicle_small_vol.id})
        self.assertIn("Overcapacity Error: Total volume", str(err.exception))
        self.assertIn("exceeds vehicle maximum volume capacity", str(err.exception))

    def test_06_unconstrained_vehicle_capacity(self):
        """Vehicles with 0.0 max capacity (unrestricted) must allow any weight and volume."""
        picking = self._create_outgoing_picking([(self.product_kopi, 5000.0)])
        picking.write({"vehicle_id": self.vehicle_unlimited.id})
        self.assertEqual(picking.vehicle_id, self.vehicle_unlimited)
