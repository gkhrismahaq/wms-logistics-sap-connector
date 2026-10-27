import uuid

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from ..constants import (
    PICKING_TYPE_CODE_OUTGOING,
    VEHICLE_STATE_AVAILABLE,
)


@tagged("post_install", "-at_install", "wms_sap")
class TestReportSuratJalan(TransactionCase):
    """Test suite for Official Surat Jalan (Delivery Slip) QWeb PDF reporting."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.driver = cls.env["res.partner"].create(
            {
                "name": "Budi Santoso",
                "is_company": False,
            }
        )

        cls.vehicle = cls.env["wms.vehicle"].create(
            {
                "license_plate": "B 1234 DISP",
                "driver_id": cls.driver.id,
                "max_weight": 1000.0,
                "max_volume": 10.0,
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
                "street": "Jl. Raya Lowokwaru No. 45",
                "city": "Malang",
                "phone": "0341-123456",
                "customer_rank": 1,
            }
        )

        cls.picking_type_out = cls.env["stock.picking.type"].search(
            [("code", "=", PICKING_TYPE_CODE_OUTGOING)], limit=1
        )
        cls.src_loc = cls.picking_type_out.default_location_src_id
        cls.dest_loc = cls.customer.property_stock_customer

        cls.report_action = cls.env.ref("wms_sap_connector.action_report_surat_jalan")

    def _create_outgoing_picking(
        self, items, vehicle=None, driver=None, sap_doc_number=None
    ):
        """Helper to create and confirm an outgoing picking with moves."""
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "partner_id": self.customer.id,
                "location_id": self.src_loc.id,
                "location_dest_id": self.dest_loc.id,
                "origin": sap_doc_number or "TEST-SJ-001",
                "sap_doc_number": sap_doc_number or "SO-SJ-2026-001",
                "vehicle_id": vehicle.id if vehicle else False,
                "driver_id": driver.id if driver else False,
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

    def test_01_report_action_and_binding(self):
        """Action report metadata and model binding must be correctly registered."""
        self.assertTrue(self.report_action.exists())
        self.assertEqual(self.report_action.model, "stock.picking")
        self.assertEqual(self.report_action.report_type, "qweb-pdf")
        self.assertEqual(
            self.report_action.report_name, "wms_sap_connector.report_surat_jalan"
        )
        self.assertEqual(self.report_action.binding_model_id.model, "stock.picking")
        self.assertEqual(self.report_action.binding_type, "report")
        group_disp = self.env.ref("wms_sap_connector.group_wms_dispatcher")
        group_mgr = self.env.ref("wms_sap_connector.group_wms_manager")
        self.assertIn(group_disp, self.report_action.groups_id)
        self.assertIn(group_mgr, self.report_action.groups_id)

    def test_02_report_rendering_happy_path(self):
        """Surat Jalan report rendering with full vehicle, driver, and cargo lines."""
        picking = self._create_outgoing_picking(
            items=[(self.product_kopi, 10.0), (self.product_teh, 20.0)],
            vehicle=self.vehicle,
            driver=self.driver,
            sap_doc_number="SO-SJ-HAPPY-001",
        )

        # 1. Test HTML rendering content
        html_bytes, _report_type = self.report_action._render_qweb_html(
            self.report_action.id, [picking.id]
        )
        html_str = (
            html_bytes.decode("utf-8")
            if isinstance(html_bytes, bytes)
            else str(html_bytes)
        )

        # Verification of essential headers & transfer information
        self.assertIn("Surat Jalan Pengantaran Barang", html_str)
        self.assertIn(picking.name, html_str)
        self.assertIn("SO-SJ-HAPPY-001", html_str)

        # Verification of customer destination
        self.assertIn("Toko Retail Makmur", html_str)
        self.assertIn("Malang", html_str)

        # Verification of fleet & driver details
        self.assertIn("B 1234 DISP", html_str)
        self.assertIn("Budi Santoso", html_str)

        # Verification of cargo items
        self.assertIn("MAT-KOPI-DISP", html_str)
        self.assertIn("Kopi Sachet 500g", html_str)
        self.assertIn("MAT-TEH-DISP", html_str)
        self.assertIn("Teh Celup Kotak 250g", html_str)

        # Verification of 3 signature blocks
        self.assertIn("Disiapkan / Dikeluarkan Oleh", html_str)
        self.assertIn("Dibawa / Diantar Oleh", html_str)
        self.assertIn("Diterima Dengan Baik Oleh", html_str)

        # 2. Test PDF rendering via _render_qweb_pdf
        pdf_bytes, _report_type = self.report_action.with_context(
            force_report_rendering=True
        )._render_qweb_pdf(self.report_action.id, [picking.id])
        self.assertTrue(isinstance(pdf_bytes, bytes))
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertEqual(pdf_bytes[:4], b"%PDF")

    def test_03_report_rendering_without_vehicle_and_driver(self):
        """Surat Jalan report rendering before vehicle/driver assignment must gracefully fallback."""
        picking = self._create_outgoing_picking(
            items=[(self.product_kopi, 5.0)],
            vehicle=None,
            driver=None,
            sap_doc_number="SO-SJ-EDGE-002",
        )

        html_bytes, _ = self.report_action._render_qweb_html(
            self.report_action.id, [picking.id]
        )
        html_str = (
            html_bytes.decode("utf-8")
            if isinstance(html_bytes, bytes)
            else str(html_bytes)
        )

        self.assertIn(picking.name, html_str)
        self.assertIn("SO-SJ-EDGE-002", html_str)
        self.assertIn("Kopi Sachet 500g", html_str)

        # Ensure PDF generates without error even with null fleet and driver
        pdf_bytes, _ = self.report_action.with_context(
            force_report_rendering=True
        )._render_qweb_pdf(self.report_action.id, [picking.id])
        self.assertTrue(isinstance(pdf_bytes, bytes))
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertEqual(pdf_bytes[:4], b"%PDF")

    def test_04_report_rendering_multi_document_batch(self):
        """Batch printing multiple Surat Jalan documents in a single PDF stream."""
        p1 = self._create_outgoing_picking(
            items=[(self.product_kopi, 2.0)],
            vehicle=self.vehicle,
            driver=self.driver,
            sap_doc_number="SO-SJ-BATCH-01",
        )
        p2 = self._create_outgoing_picking(
            items=[(self.product_teh, 4.0)],
            vehicle=self.vehicle,
            driver=self.driver,
            sap_doc_number="SO-SJ-BATCH-02",
        )

        pdf_bytes, _ = self.report_action.with_context(
            force_report_rendering=True
        )._render_qweb_pdf(self.report_action.id, [p1.id, p2.id])
        self.assertTrue(isinstance(pdf_bytes, bytes))
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertEqual(pdf_bytes[:4], b"%PDF")
        self.assertTrue(isinstance(pdf_bytes, bytes))
        self.assertGreater(len(pdf_bytes), 2000)
        self.assertEqual(pdf_bytes[:4], b"%PDF")

    def test_05_report_security_role_based_access_control(self):
        """Surat Jalan report access is restricted to Dispatchers and Managers; Operators are blocked."""
        group_op = self.env.ref("wms_sap_connector.group_wms_operator")
        group_disp = self.env.ref("wms_sap_connector.group_wms_dispatcher")
        group_mgr = self.env.ref("wms_sap_connector.group_wms_manager")

        uid_suffix = uuid.uuid4().hex[:6]
        user_operator = self.env["res.users"].create(
            {
                "name": f"Operator Report Test {uid_suffix}",
                "login": f"op_rep_{uid_suffix}@example.com",
                "groups_id": [(6, 0, [group_op.id])],
            }
        )
        user_dispatcher = self.env["res.users"].create(
            {
                "name": f"Dispatcher Report Test {uid_suffix}",
                "login": f"disp_rep_{uid_suffix}@example.com",
                "groups_id": [(6, 0, [group_disp.id])],
            }
        )
        user_manager = self.env["res.users"].create(
            {
                "name": f"Manager Report Test {uid_suffix}",
                "login": f"mgr_rep_{uid_suffix}@example.com",
                "groups_id": [(6, 0, [group_mgr.id])],
            }
        )

        picking = self._create_outgoing_picking(
            items=[(self.product_kopi, 1.0)],
            vehicle=self.vehicle,
            driver=self.driver,
            sap_doc_number=f"SO-SJ-SEC-{uid_suffix}",
        )

        # 1. Operator is blocked from rendering Surat Jalan
        with self.assertRaises(AccessError):
            self.report_action.with_user(user_operator)._render_qweb_html(
                self.report_action.id, [picking.id]
            )

        # 2. Dispatcher can render Surat Jalan
        html_disp, _ = self.report_action.with_user(user_dispatcher)._render_qweb_html(
            self.report_action.id, [picking.id]
        )
        self.assertTrue(len(html_disp) > 0)

        # 3. Manager can render Surat Jalan
        html_mgr, _ = self.report_action.with_user(user_manager)._render_qweb_html(
            self.report_action.id, [picking.id]
        )
        self.assertTrue(len(html_mgr) > 0)

