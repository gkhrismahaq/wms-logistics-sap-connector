import base64
import json
import uuid
from unittest.mock import MagicMock, patch

import requests
from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from ..constants import (
    CONFIG_PARAM_SAP_API_TOKEN,
    CONFIG_PARAM_SAP_BASE_URL,
    DIRECTION_OUTBOUND,
    PICKING_TYPE_CODE_OUTGOING,
    SYNC_STATUS_FAILED,
    SYNC_STATUS_SUCCESS,
    SYNC_STATUS_SYNCED,
    SYNC_TYPE_OUTBOUND_SO,
    WEBHOOK_STATUS_GOODS_ISSUED,
)


@tagged("post_install", "-at_install", "wms_sap")
class TestWebhookGoodsIssue(TransactionCase):
    """Test suite for Goods Issue & POD Webhook notification to SAP Upper Line."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            CONFIG_PARAM_SAP_BASE_URL, "http://mock-sap:8000"
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            CONFIG_PARAM_SAP_API_TOKEN, "secret_sap_token_gi_123"
        )

        cls.customer = cls.env["res.partner"].create(
            {
                "name": "PT Sumber Alfaria Trijaya",
                "sap_partner_code": "CUST-ALFAMART-01",
                "customer_rank": 1,
            }
        )

        cls.product = cls.env["product.product"].search(
            [("sap_material_code", "=", "MAT-KOPI-01")], limit=1
        )
        if not cls.product:
            cls.product = cls.env["product.product"].create(
                {
                    "name": "Kopi Kapal Api Special Mix",
                    "sap_material_code": "MAT-KOPI-01",
                    "type": "product",
                }
            )

        cls.picking_type_out = cls.env["stock.picking.type"].search(
            [("code", "=", PICKING_TYPE_CODE_OUTGOING)], limit=1
        )
        cls.src_loc = cls.picking_type_out.default_location_src_id
        cls.dest_loc = cls.customer.property_stock_customer

        # Ensure source location has ample stock for delivery validation
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.src_loc, 100.0
        )

        cls.dummy_pod = base64.b64encode(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    def _create_outgoing_picking(self, doc_num, with_pod=True):
        """Helper to create and assign an outgoing delivery picking with or without POD."""
        vals = {
            "picking_type_id": self.picking_type_out.id,
            "partner_id": self.customer.id,
            "location_id": self.src_loc.id,
            "location_dest_id": self.dest_loc.id,
            "origin": doc_num,
            "sap_doc_number": doc_num,
        }
        if with_pod:
            vals.update(
                {
                    "proof_of_delivery": self.dummy_pod,
                    "pod_signed_by": "Budi Santoso (Store Manager)",
                    "pod_timestamp": fields.Datetime.now(),
                }
            )
        picking = self.env["stock.picking"].create(vals)
        # Create move and reserve stock
        self.env["stock.move"].create(
            {
                "name": "Test Goods Issue Move",
                "picking_id": picking.id,
                "product_id": self.product.id,
                "product_uom_qty": 5.0,
                "product_uom": self.product.uom_id.id,
                "location_id": self.src_loc.id,
                "location_dest_id": self.dest_loc.id,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        for m in picking.move_ids:
            m.quantity = m.product_uom_qty
            m.picked = True
        return picking

    @patch("requests.post")
    def test_01_webhook_goods_issue_success(self, mock_post):
        """REQ-POD-03: Validation of outgoing picking with POD triggers Goods Issue webhook and logs accounting."""
        doc_num = f"SO-GI-OK-{uuid.uuid4().hex[:6].upper()}"
        picking = self._create_outgoing_picking(doc_num, with_pod=True)
        self.assertTrue(picking.has_pod)

        # Mock SAP 200 response with sap_accounting_log
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(
            {
                "status": "SUCCESS",
                "code": 200,
                "message": "Goods Issue and POD acknowledged in SAP Financials",
                "sap_accounting_log": {
                    "journal_entry": "JE-SAP-2026-9902",
                    "posting_date": "2026-10-26",
                    "debit_account": "501.001 - Harga Pokok Penjualan (HPP) (Rp 25.000.000)",
                    "credit_account": "101.001 - Persediaan Barang Jadi (Rp 25.000.000)",
                    "financial_status": "POSTED",
                },
            }
        )
        mock_post.return_value = mock_response

        # Validate picking via official button_validate
        picking.button_validate()

        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_SYNCED)

        # Verify requests.post call arguments
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://mock-sap:8000/api/sap/goods-issue")
        posted_data = json.loads(kwargs["data"])
        self.assertEqual(posted_data["sap_doc_number"], doc_num)
        self.assertEqual(posted_data["status"], WEBHOOK_STATUS_GOODS_ISSUED)
        self.assertEqual(posted_data["receiver_name"], "Budi Santoso (Store Manager)")
        self.assertTrue(posted_data["has_pod"])
        self.assertIn("Authorization", kwargs["headers"])

        # Verify audit log entry in sap.sync.log
        log = self.env["sap.sync.log"].search(
            [
                ("sync_type", "=", SYNC_TYPE_OUTBOUND_SO),
                ("direction", "=", DIRECTION_OUTBOUND),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(log)
        self.assertEqual(log.status, SYNC_STATUS_SUCCESS)
        self.assertIn("JE-SAP-2026-9902", log.payload)

    @patch("requests.post")
    def test_02_validation_without_pod_does_not_trigger_webhook(self, mock_post):
        """REQ-POD-03: Validation of outgoing picking without POD MUST NOT trigger webhook."""
        doc_num = f"SO-GI-NOPOD-{uuid.uuid4().hex[:6].upper()}"
        picking = self._create_outgoing_picking(doc_num, with_pod=False)
        self.assertFalse(picking.has_pod)

        picking.button_validate()

        self.assertEqual(picking.state, "done")
        self.assertNotEqual(picking.sap_sync_status, SYNC_STATUS_SYNCED)
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_03_late_pod_upload_triggers_webhook_on_done_picking(self, mock_post):
        """REQ-POD-03: Uploading POD to an already-done picking triggers Goods Issue webhook automatically."""
        doc_num = f"SO-GI-LATE-{uuid.uuid4().hex[:6].upper()}"
        picking = self._create_outgoing_picking(doc_num, with_pod=False)
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertFalse(picking.has_pod)
        mock_post.assert_not_called()

        # Mock SAP 200 response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(
            {
                "status": "SUCCESS",
                "code": 200,
                "message": "Late POD acknowledged",
                "sap_accounting_log": {"journal_entry": "JE-SAP-LATE-01"},
            }
        )
        mock_post.return_value = mock_response

        # Upload POD to done picking
        picking.write(
            {
                "proof_of_delivery": self.dummy_pod,
                "pod_signed_by": "Joko Susilo (Penerima)",
            }
        )

        self.assertTrue(picking.has_pod)
        mock_post.assert_called_once()
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_SYNCED)

    @patch("requests.post")
    def test_04_webhook_goods_issue_non_blocking_failure(self, mock_post):
        """REQ-POD-03: Connection failure marks status failed without blocking physical completion."""
        doc_num = f"SO-GI-FAIL-{uuid.uuid4().hex[:6].upper()}"
        picking = self._create_outgoing_picking(doc_num, with_pod=True)

        mock_post.side_effect = requests.exceptions.ConnectionError(
            "Could not connect to SAP server on port 8000"
        )

        picking.button_validate()

        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_FAILED)

        # Verify failed audit log
        log = self.env["sap.sync.log"].search(
            [
                ("sync_type", "=", SYNC_TYPE_OUTBOUND_SO),
                ("direction", "=", DIRECTION_OUTBOUND),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(log)
        self.assertEqual(log.status, SYNC_STATUS_FAILED)
        self.assertIn("Could not connect to SAP", log.error_message)

    @patch("requests.post")
    def test_05_manual_retry_button_goods_issue(self, mock_post):
        """REQ-POD-03: action_send_sap_goods_issue_webhook allows manual retry and updates status."""
        doc_num = f"SO-GI-RETRY-{uuid.uuid4().hex[:6].upper()}"
        picking = self._create_outgoing_picking(doc_num, with_pod=True)

        # 1. First attempt fails
        mock_post.side_effect = requests.exceptions.Timeout("SAP Timeout")
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_FAILED)

        # 2. Second attempt via button succeeds
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(
            {
                "status": "SUCCESS",
                "code": 200,
                "message": "Retry Goods Issue successfully processed",
            }
        )
        mock_post.side_effect = None
        mock_post.return_value = mock_response

        res = picking.action_send_sap_goods_issue_webhook()
        self.assertTrue(res)
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_SYNCED)

    def test_06_missing_sap_base_url_handling(self):
        """REQ-POD-03: When SAP Base URL is not configured, webhook marks failed cleanly with log entry."""
        self.env["ir.config_parameter"].sudo().set_param(
            CONFIG_PARAM_SAP_BASE_URL, False
        )
        doc_num = f"SO-GI-NOURL-{uuid.uuid4().hex[:6].upper()}"
        picking = self._create_outgoing_picking(doc_num, with_pod=True)

        picking.button_validate()

        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_FAILED)

        log = self.env["sap.sync.log"].search(
            [
                ("sync_type", "=", SYNC_TYPE_OUTBOUND_SO),
                ("direction", "=", DIRECTION_OUTBOUND),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(log)
        self.assertEqual(log.status, SYNC_STATUS_FAILED)
        self.assertIn("SAP Base URL not configured", log.error_message)
