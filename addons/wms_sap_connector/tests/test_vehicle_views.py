"""Test suite for WMS Vehicle UI Views, Actions, and Menus.

Validates tree, form, search views, window action, and menu structure for wms.vehicle.
"""

import uuid

from odoo.tests.common import TransactionCase, tagged

from ..constants import (
    VEHICLE_STATE_AVAILABLE,
    VEHICLE_STATE_MAINTENANCE,
    VEHICLE_STATE_ON_DELIVERY,
)


@tagged("post_install", "-at_install", "wms_sap")
class TestVehicleViews(TransactionCase):
    """Unit test cases for wms.vehicle UI views, action window, and menus."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.driver = cls.env["res.partner"].create(
            {
                "name": f"Driver View Test {uuid.uuid4().hex[:4]}",
                "is_company": False,
            }
        )

        cls.v_avail = cls.env["wms.vehicle"].create(
            {
                "license_plate": f"B {uuid.uuid4().hex[:4].upper()} AV",
                "driver_id": cls.driver.id,
                "max_weight": 2000.0,
                "max_volume": 10.0,
                "state": VEHICLE_STATE_AVAILABLE,
            }
        )
        cls.v_delivery = cls.env["wms.vehicle"].create(
            {
                "license_plate": f"B {uuid.uuid4().hex[:4].upper()} OD",
                "driver_id": cls.driver.id,
                "max_weight": 3000.0,
                "max_volume": 15.0,
                "state": VEHICLE_STATE_ON_DELIVERY,
            }
        )
        cls.v_maint = cls.env["wms.vehicle"].create(
            {
                "license_plate": f"B {uuid.uuid4().hex[:4].upper()} MT",
                "driver_id": cls.driver.id,
                "max_weight": 1500.0,
                "max_volume": 8.0,
                "state": VEHICLE_STATE_MAINTENANCE,
            }
        )

    def test_01_vehicle_views_definition(self):
        """Test tree, form, and search views must be defined and valid."""
        tree_view = self.env.ref("wms_sap_connector.view_wms_vehicle_tree")
        self.assertTrue(tree_view)
        self.assertEqual(tree_view.model, "wms.vehicle")
        arch_tree = self.env["wms.vehicle"].get_view(tree_view.id, "tree")
        self.assertIn("license_plate", arch_tree["arch"])
        self.assertIn("state", arch_tree["arch"])

        form_view = self.env.ref("wms_sap_connector.view_wms_vehicle_form")
        self.assertTrue(form_view)
        self.assertEqual(form_view.model, "wms.vehicle")
        arch_form = self.env["wms.vehicle"].get_view(form_view.id, "form")
        self.assertIn("license_plate", arch_form["arch"])
        self.assertIn("statusbar", arch_form["arch"])

        search_view = self.env.ref("wms_sap_connector.view_wms_vehicle_search")
        self.assertTrue(search_view)
        self.assertEqual(search_view.model, "wms.vehicle")
        arch_search = self.env["wms.vehicle"].get_view(search_view.id, "search")
        self.assertIn("filter_available", arch_search["arch"])
        self.assertIn("group_by_state", arch_search["arch"])

    def test_02_vehicle_action_and_menus(self):
        """Test window action and menu hierarchy must be correctly configured."""
        action = self.env.ref("wms_sap_connector.action_wms_vehicle")
        self.assertTrue(action)
        self.assertEqual(action.res_model, "wms.vehicle")
        self.assertEqual(action.view_mode, "tree,form")

        menu_root = self.env.ref("wms_sap_connector.menu_wms_logistics_root")
        self.assertTrue(menu_root)
        self.assertEqual(
            menu_root.parent_id.id, self.env.ref("stock.menu_stock_root").id
        )

        menu_vehicle = self.env.ref("wms_sap_connector.menu_wms_vehicle")
        self.assertTrue(menu_vehicle)
        self.assertEqual(menu_vehicle.parent_id.id, menu_root.id)
        self.assertEqual(menu_vehicle.action.id, action.id)

    def test_03_search_and_filters_execution(self):
        """Test filter domain and search fields return accurate records."""
        # 1. Search by exact license plate
        res_plate = self.env["wms.vehicle"].search(
            [("license_plate", "=", self.v_avail.license_plate)]
        )
        self.assertEqual(res_plate.id, self.v_avail.id)

        # 2. Search by driver
        res_driver = self.env["wms.vehicle"].search(
            [("driver_id", "=", self.driver.id)]
        )
        self.assertEqual(len(res_driver), 3)

        # 3. Filter available state
        res_avail = self.env["wms.vehicle"].search(
            [
                ("state", "=", VEHICLE_STATE_AVAILABLE),
                ("driver_id", "=", self.driver.id),
            ]
        )
        self.assertEqual(len(res_avail), 1)
        self.assertEqual(res_avail.id, self.v_avail.id)

        # 4. Filter on_delivery state
        res_od = self.env["wms.vehicle"].search(
            [
                ("state", "=", VEHICLE_STATE_ON_DELIVERY),
                ("driver_id", "=", self.driver.id),
            ]
        )
        self.assertEqual(len(res_od), 1)
        self.assertEqual(res_od.id, self.v_delivery.id)

        # 5. Filter maintenance state
        res_mt = self.env["wms.vehicle"].search(
            [
                ("state", "=", VEHICLE_STATE_MAINTENANCE),
                ("driver_id", "=", self.driver.id),
            ]
        )
        self.assertEqual(len(res_mt), 1)
        self.assertEqual(res_mt.id, self.v_maint.id)
