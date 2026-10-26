import uuid

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "wms_sap")
class TestPutawayAllocation(TransactionCase):
    """Test suite for Putaway Bin Allocation and Security Access Rules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env["stock.location"].search(
            [("complete_name", "=", "DCLOW/Stock")], limit=1
        )
        cls.shelf1_location = cls.env["stock.location"].search(
            [("complete_name", "=", "DCLOW/Stock/Shelf 1")], limit=1
        )
        cls.shelf2_location = cls.env["stock.location"].search(
            [("complete_name", "=", "DCLOW/Stock/Shelf 2")], limit=1
        )

        cls.vendor = cls.env["res.partner"].search(
            [("sap_partner_code", "=", "VEND-INDOMARCO")], limit=1
        )
        if not cls.vendor:
            cls.vendor = cls.env["res.partner"].create(
                {
                    "name": "PT Indomarco Prismatama",
                    "sap_partner_code": "VEND-INDOMARCO",
                    "supplier_rank": 1,
                }
            )

        cls.product_kopi = cls.env["product.product"].search(
            [("sap_material_code", "=", "MAT-KOPI-01")], limit=1
        )
        cls.product_pucuk = cls.env["product.product"].search(
            [("sap_material_code", "=", "MAT-PUCUK-01")], limit=1
        )
        cls.product_unmapped = cls.env["product.product"].search(
            [("sap_material_code", "=", "MAT-BERAS-05")], limit=1
        )
        if not cls.product_unmapped:
            cls.product_unmapped = cls.env["product.product"].create(
                {
                    "name": "Beras Premium Maknyuss 5kg",
                    "sap_material_code": "MAT-BERAS-05",
                    "type": "product",
                }
            )

        # Test users for security validation
        group_operator = cls.env.ref("wms_sap_connector.group_wms_operator")
        group_manager = cls.env.ref("wms_sap_connector.group_wms_manager")

        cls.user_operator = cls.env["res.users"].create(
            {
                "name": "WMS Test Operator",
                "login": f"test_operator_{uuid.uuid4().hex[:6]}",
                "email": "operator_test@example.com",
                "groups_id": [(6, 0, [group_operator.id])],
            }
        )
        cls.user_manager = cls.env["res.users"].create(
            {
                "name": "WMS Test Manager",
                "login": f"test_manager_{uuid.uuid4().hex[:6]}",
                "email": "manager_test@example.com",
                "groups_id": [(6, 0, [group_manager.id])],
            }
        )

    def test_01_putaway_allocation_mapped_products(self):
        """REQ-INB-06: Mapped products must automatically allocate destination shelves."""
        doc_num = f"PO-TEST-PUTAWAY-{uuid.uuid4().hex[:6].upper()}"
        payload = {
            "sap_doc_number": doc_num,
            "vendor_code": "VEND-INDOMARCO",
            "items": [
                {"sap_material_code": "MAT-KOPI-01", "qty": 10},
                {"sap_material_code": "MAT-PUCUK-01", "qty": 20},
            ],
        }

        picking, is_created = self.env["stock.picking"].create_inbound_from_sap(payload)
        self.assertTrue(is_created)
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(len(picking.move_line_ids), 2)

        ml_kopi = picking.move_line_ids.filtered(
            lambda l: l.product_id.sap_material_code == "MAT-KOPI-01"
        )
        ml_pucuk = picking.move_line_ids.filtered(
            lambda l: l.product_id.sap_material_code == "MAT-PUCUK-01"
        )

        self.assertEqual(ml_kopi.location_dest_id.id, self.shelf1_location.id)
        self.assertEqual(ml_pucuk.location_dest_id.id, self.shelf2_location.id)

    def test_02_putaway_fallback_unmapped_product(self):
        """REQ-INB-06: Unmapped products must fallback safely to warehouse main stock location."""
        doc_num = f"PO-TEST-FALLBACK-{uuid.uuid4().hex[:6].upper()}"
        payload = {
            "sap_doc_number": doc_num,
            "vendor_code": "VEND-INDOMARCO",
            "items": [
                {"sap_material_code": "MAT-BERAS-05", "qty": 5},
            ],
        }

        picking, is_created = self.env["stock.picking"].create_inbound_from_sap(payload)
        self.assertTrue(is_created)
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(len(picking.move_line_ids), 1)

        ml_unmapped = picking.move_line_ids[0]
        self.assertEqual(ml_unmapped.location_dest_id.id, self.stock_location.id)

    def test_03_security_putaway_rule_access(self):
        """REQ-INB-07: Operator has read-only access while Manager has full CRUD on putaway rules."""
        # 1. Operator can read
        rules_operator = (
            self.env["stock.putaway.rule"].with_user(self.user_operator).search([])
        )
        self.assertTrue(len(rules_operator) >= 1)

        # 2. Operator cannot create
        with self.assertRaises(AccessError):
            self.env["stock.putaway.rule"].with_user(self.user_operator).create(
                {
                    "product_id": self.product_kopi.id,
                    "location_in_id": self.stock_location.id,
                    "location_out_id": self.shelf2_location.id,
                }
            )

        # 3. Manager can create, write, and unlink
        rule_manager = (
            self.env["stock.putaway.rule"]
            .with_user(self.user_manager)
            .create(
                {
                    "product_id": self.product_kopi.id,
                    "location_in_id": self.stock_location.id,
                    "location_out_id": self.shelf2_location.id,
                    "sequence": 99,
                }
            )
        )
        self.assertTrue(rule_manager.id)

        rule_manager.write({"sequence": 98})
        self.assertEqual(rule_manager.sequence, 98)

        rule_manager.unlink()
