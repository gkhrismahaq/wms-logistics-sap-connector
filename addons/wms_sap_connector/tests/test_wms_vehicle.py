# -*- coding: utf-8 -*-
"""Test suite for WMS Vehicle Model and Security Access Control.

Validates REQ-FLT-01 (wms.vehicle attributes, unique constraint, non-negative capacity)
and REQ-FLT-02 (role-based access control for Dispatcher, Manager, and Operator).
"""

import uuid
from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

from ..constants import (
    VEHICLE_STATE_AVAILABLE,
    VEHICLE_STATE_MAINTENANCE,
    VEHICLE_STATE_ON_DELIVERY,
)


@tagged("post_install", "-at_install", "wms_sap")
class TestWmsVehicle(TransactionCase):
    """Unit test cases for wms.vehicle model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.driver = cls.env["res.partner"].create(
            {
                "name": "Budi Santoso (Driver)",
                "is_company": False,
            }
        )

        group_operator = cls.env.ref("wms_sap_connector.group_wms_operator")
        group_dispatcher = cls.env.ref("wms_sap_connector.group_wms_dispatcher")
        group_manager = cls.env.ref("wms_sap_connector.group_wms_manager")

        cls.user_operator = cls.env["res.users"].create(
            {
                "name": "WMS Fleet Operator",
                "login": f"test_op_fleet_{uuid.uuid4().hex[:6]}",
                "email": "op_fleet@example.com",
                "groups_id": [(6, 0, [group_operator.id])],
            }
        )
        cls.user_dispatcher = cls.env["res.users"].create(
            {
                "name": "WMS Fleet Dispatcher",
                "login": f"test_disp_fleet_{uuid.uuid4().hex[:6]}",
                "email": "disp_fleet@example.com",
                "groups_id": [(6, 0, [group_dispatcher.id])],
            }
        )
        cls.user_manager = cls.env["res.users"].create(
            {
                "name": "WMS Fleet Manager",
                "login": f"test_mgr_fleet_{uuid.uuid4().hex[:6]}",
                "email": "mgr_fleet@example.com",
                "groups_id": [(6, 0, [group_manager.id])],
            }
        )

    def test_01_create_vehicle_happy_path(self):
        """REQ-FLT-01: Successfully create vehicle with valid attributes."""
        plate = f"B {uuid.uuid4().hex[:4].upper()} WMS"
        vehicle = self.env["wms.vehicle"].create(
            {
                "license_plate": plate.lower(),
                "driver_id": self.driver.id,
                "max_weight": 2500.0,
                "max_volume": 12.5,
            }
        )

        self.assertTrue(vehicle.id)
        # Verify license plate uppercase normalization and rec_name
        self.assertEqual(vehicle.license_plate, plate)
        self.assertEqual(vehicle.display_name, plate)
        self.assertEqual(vehicle.state, VEHICLE_STATE_AVAILABLE)
        self.assertEqual(vehicle.driver_id.id, self.driver.id)
        self.assertEqual(vehicle.max_weight, 2500.0)
        self.assertEqual(vehicle.max_volume, 12.5)

        # Verify state transitions
        vehicle.write({"state": VEHICLE_STATE_ON_DELIVERY})
        self.assertEqual(vehicle.state, VEHICLE_STATE_ON_DELIVERY)
        vehicle.write({"state": VEHICLE_STATE_MAINTENANCE})
        self.assertEqual(vehicle.state, VEHICLE_STATE_MAINTENANCE)

    def test_02_duplicate_license_plate_constraint(self):
        """REQ-FLT-01: Duplicate license plate must be rejected by SQL unique constraint."""
        plate = f"B {uuid.uuid4().hex[:4].upper()} UNQ"
        self.env["wms.vehicle"].create(
            {
                "license_plate": plate,
                "max_weight": 1000.0,
                "max_volume": 5.0,
            }
        )

        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.env["wms.vehicle"].create(
                    {
                        "license_plate": plate,
                        "max_weight": 1500.0,
                        "max_volume": 8.0,
                    }
                )

    def test_03_capacity_validation_negative_values(self):
        """REQ-FLT-01: Negative capacity for weight or volume must raise ValidationError."""
        # Negative weight
        with self.assertRaises(ValidationError):
            self.env["wms.vehicle"].create(
                {
                    "license_plate": f"B {uuid.uuid4().hex[:4].upper()} NEG1",
                    "max_weight": -100.0,
                    "max_volume": 10.0,
                }
            )

        # Negative volume
        with self.assertRaises(ValidationError):
            self.env["wms.vehicle"].create(
                {
                    "license_plate": f"B {uuid.uuid4().hex[:4].upper()} NEG2",
                    "max_weight": 100.0,
                    "max_volume": -5.0,
                }
            )

    def test_04_security_vehicle_access_rights(self):
        """REQ-FLT-02: Dispatcher & Manager have full CRUD, Operator is read-only."""
        plate_disp = f"B {uuid.uuid4().hex[:4].upper()} DSP"

        # 1. Dispatcher can CREATE, WRITE, READ, UNLINK
        vehicle_disp = (
            self.env["wms.vehicle"]
            .with_user(self.user_dispatcher)
            .create(
                {
                    "license_plate": plate_disp,
                    "driver_id": self.driver.id,
                    "max_weight": 3000.0,
                    "max_volume": 15.0,
                }
            )
        )
        self.assertTrue(vehicle_disp.id)

        vehicle_disp.with_user(self.user_dispatcher).write({"max_weight": 3500.0})
        self.assertEqual(vehicle_disp.max_weight, 3500.0)

        # 2. Operator CAN READ
        vehicles_op = (
            self.env["wms.vehicle"]
            .with_user(self.user_operator)
            .search([("id", "=", vehicle_disp.id)])
        )
        self.assertEqual(len(vehicles_op), 1)

        # 3. Operator CANNOT CREATE
        with self.assertRaises(AccessError):
            self.env["wms.vehicle"].with_user(self.user_operator).create(
                {
                    "license_plate": f"B {uuid.uuid4().hex[:4].upper()} OPR",
                    "max_weight": 1000.0,
                    "max_volume": 5.0,
                }
            )

        # 4. Operator CANNOT WRITE
        with self.assertRaises(AccessError):
            vehicle_disp.with_user(self.user_operator).write({"max_weight": 4000.0})

        # 5. Operator CANNOT UNLINK
        with self.assertRaises(AccessError):
            vehicle_disp.with_user(self.user_operator).unlink()

        # 6. Manager CAN WRITE & UNLINK
        vehicle_disp.with_user(self.user_manager).write({"state": VEHICLE_STATE_MAINTENANCE})
        self.assertEqual(vehicle_disp.state, VEHICLE_STATE_MAINTENANCE)

        vehicle_disp.with_user(self.user_manager).unlink()
        self.assertFalse(self.env["wms.vehicle"].search([("license_plate", "=", plate_disp)]))
