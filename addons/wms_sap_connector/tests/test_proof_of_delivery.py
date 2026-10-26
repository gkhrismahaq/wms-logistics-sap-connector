import base64
from datetime import datetime, timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from ..constants import (
    PICKING_TYPE_CODE_OUTGOING,
)


@tagged("post_install", "-at_install", "wms_sap")
class TestProofOfDelivery(TransactionCase):
    """Test suite for Proof of Delivery (POD) fields, automation, and search filters."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Toko Retail Sentosa",
                "street": "Jl. Kawi No. 12",
                "city": "Malang",
                "customer_rank": 1,
            }
        )

        cls.picking_type_out = cls.env["stock.picking.type"].search(
            [("code", "=", PICKING_TYPE_CODE_OUTGOING)], limit=1
        )
        cls.src_loc = cls.picking_type_out.default_location_src_id
        cls.dest_loc = cls.customer.property_stock_customer

        # Sample dummy 1x1 PNG base64 byte string for testing binary field
        cls.dummy_pod_bytes = base64.b64encode(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    def _create_outgoing_picking(self, sap_doc="SO-POD-TEST-001"):
        """Helper to create an outgoing delivery picking."""
        return self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "partner_id": self.customer.id,
                "location_id": self.src_loc.id,
                "location_dest_id": self.dest_loc.id,
                "origin": sap_doc,
                "sap_doc_number": sap_doc,
            }
        )

    def test_01_pod_fields_initial_state_and_computation(self):
        """A new picking starts without POD, and computing has_pod updates correctly."""
        picking = self._create_outgoing_picking("SO-POD-INIT-01")

        self.assertFalse(picking.has_pod)
        self.assertFalse(picking.proof_of_delivery)
        self.assertFalse(picking.pod_signed_by)
        self.assertFalse(picking.pod_timestamp)

        # Update with receiver name only
        picking.write({"pod_signed_by": "Ahmad Subagio"})
        self.assertTrue(picking.has_pod)
        self.assertTrue(bool(picking.pod_timestamp))

    def test_02_onchange_pod_fields_populates_timestamp(self):
        """Setting proof_of_delivery or pod_signed_by in UI onchange must auto-populate timestamp."""
        picking = self.env["stock.picking"].new(
            {
                "picking_type_id": self.picking_type_out.id,
                "partner_id": self.customer.id,
            }
        )
        self.assertFalse(picking.pod_timestamp)

        picking.proof_of_delivery = self.dummy_pod_bytes
        picking._onchange_pod_fields()

        self.assertTrue(bool(picking.pod_timestamp))
        self.assertAlmostEqual(
            picking.pod_timestamp.timestamp(),
            fields.Datetime.now().timestamp(),
            delta=5,
        )

    def test_03_pod_write_and_manual_timestamp_override(self):
        """User-specified manual timestamp must be preserved and not overwritten."""
        picking = self._create_outgoing_picking("SO-POD-MANUAL-01")
        custom_dt = datetime.now() - timedelta(days=2)

        picking.write(
            {
                "proof_of_delivery": self.dummy_pod_bytes,
                "pod_signed_by": "Ibu Siti Rohmah",
                "pod_timestamp": custom_dt,
            }
        )

        self.assertTrue(picking.has_pod)
        self.assertEqual(picking.pod_signed_by, "Ibu Siti Rohmah")
        self.assertEqual(
            picking.pod_timestamp.replace(microsecond=0),
            custom_dt.replace(microsecond=0),
        )

    def test_04_pod_search_filters(self):
        """Search filters 'Has POD' and 'Missing POD' must accurately filter picking records."""
        p_with_pod = self._create_outgoing_picking("SO-POD-WITH-01")
        p_with_pod.write(
            {
                "proof_of_delivery": self.dummy_pod_bytes,
                "pod_signed_by": "Penerima Sah",
            }
        )

        p_without_pod = self._create_outgoing_picking("SO-POD-WITHOUT-01")

        # Test filter "Has POD"
        pickings_has_pod = self.env["stock.picking"].search(
            [("id", "in", (p_with_pod.id, p_without_pod.id)), ("has_pod", "=", True)]
        )
        self.assertIn(p_with_pod, pickings_has_pod)
        self.assertNotIn(p_without_pod, pickings_has_pod)

        # Test filter "Missing POD"
        pickings_missing_pod = self.env["stock.picking"].search(
            [
                ("id", "in", (p_with_pod.id, p_without_pod.id)),
                ("picking_type_code", "=", "outgoing"),
                ("has_pod", "=", False),
            ]
        )
        self.assertIn(p_without_pod, pickings_missing_pod)
        self.assertNotIn(p_with_pod, pickings_missing_pod)

    def test_05_pod_security_access(self):
        """Users in dispatcher and operator groups must have permissions to record POD."""
        group_dispatcher = self.env.ref("wms_sap_connector.group_wms_dispatcher")
        dispatcher_user = self.env["res.users"].create(
            {
                "name": "Test Dispatcher POD",
                "login": "test_disp_pod",
                "groups_id": [(6, 0, [group_dispatcher.id])],
            }
        )

        picking = self._create_outgoing_picking("SO-POD-SEC-01")

        # Dispatcher updates POD
        picking.with_user(dispatcher_user).write(
            {
                "pod_signed_by": "Pak Joko (Penerima Toko)",
                "proof_of_delivery": self.dummy_pod_bytes,
            }
        )

        self.assertTrue(picking.has_pod)
        self.assertEqual(picking.pod_signed_by, "Pak Joko (Penerima Toko)")
