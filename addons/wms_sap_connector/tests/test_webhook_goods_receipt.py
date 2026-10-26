import json
import uuid
from unittest.mock import MagicMock, patch

import requests
from odoo.tests.common import TransactionCase, tagged

from ..constants import (
    CONFIG_PARAM_SAP_API_TOKEN,
    CONFIG_PARAM_SAP_BASE_URL,
    DIRECTION_OUTBOUND,
    SYNC_STATUS_FAILED,
    SYNC_STATUS_SUCCESS,
    SYNC_STATUS_SYNCED,
    SYNC_TYPE_INBOUND_PO,
    WEBHOOK_STATUS_GOODS_RECEIVED,
)


@tagged("post_install", "-at_install", "wms_sap")
class TestWebhookGoodsReceipt(TransactionCase):
    """Test suite for Goods Receipt Webhook notification to SAP Upper Line."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            CONFIG_PARAM_SAP_BASE_URL, "http://mock-sap:8000"
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            CONFIG_PARAM_SAP_API_TOKEN, "secret_sap_token_123"
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

    def _create_assigned_picking(self, doc_num):
        payload = {
            "sap_doc_number": doc_num,
            "vendor_code": "VEND-INDOMARCO",
            "items": [
                {"sap_material_code": "MAT-KOPI-01", "qty": 10},
            ],
        }
        picking, _is_created = self.env["stock.picking"].create_inbound_from_sap(
            payload
        )
        self.assertEqual(picking.state, "assigned")
        return picking

    @patch("requests.post")
    def test_01_webhook_goods_receipt_success(self, mock_post):
        """REQ-WHK-01: Successful validation automatically triggers webhook and logs accounting journal."""
        doc_num = f"PO-TEST-WHK-OK-{uuid.uuid4().hex[:6].upper()}"
        picking = self._create_assigned_picking(doc_num)

        # Mock SAP 200 response with sap_accounting_log
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(
            {
                "status": "SUCCESS",
                "code": 200,
                "message": "Goods Receipt posted into SAP General Ledger",
                "sap_accounting_log": {
                    "journal_entry": "JE-SAP-2026-8801",
                    "posting_date": "2026-10-26",
                    "debit_account": "101.001 - Persediaan Barang Masuk",
                    "credit_account": "201.001 - Hutang Dagang Belum Difakturkan",
                    "financial_status": "POSTED",
                },
            }
        )
        mock_post.return_value = mock_response

        # Fulfill move line quantities and validate
        for line in picking.move_line_ids:
            line.quantity = line.quantity_product_uom or 10
        picking.button_validate()

        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_SYNCED)

        # Verify requests.post was called with expected payload
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://mock-sap:8000/api/sap/goods-receipt")
        posted_data = json.loads(kwargs["data"])
        self.assertEqual(posted_data["sap_doc_number"], doc_num)
        self.assertEqual(posted_data["status"], WEBHOOK_STATUS_GOODS_RECEIVED)

        # Verify audit log entry
        log = self.env["sap.sync.log"].search(
            [
                ("sync_type", "=", SYNC_TYPE_INBOUND_PO),
                ("direction", "=", DIRECTION_OUTBOUND),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(log)
        self.assertEqual(log.status, SYNC_STATUS_SUCCESS)
        self.assertIn("JE-SAP-2026-8801", log.payload)

    @patch("requests.post")
    def test_02_webhook_goods_receipt_non_blocking_failure(self, mock_post):
        """REQ-WHK-01 & REQ-WHK-02: Network failure marks failed without blocking picking validation."""
        doc_num = f"PO-TEST-WHK-FAIL-{uuid.uuid4().hex[:6].upper()}"
        picking = self._create_assigned_picking(doc_num)

        mock_post.side_effect = requests.exceptions.ConnectionError(
            "SAP server connection refused"
        )

        for line in picking.move_line_ids:
            line.quantity = line.quantity_product_uom or 10
        picking.button_validate()

        # Physical picking remains done!
        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_FAILED)

        # Verify failed audit log
        log = self.env["sap.sync.log"].search(
            [
                ("sync_type", "=", SYNC_TYPE_INBOUND_PO),
                ("direction", "=", DIRECTION_OUTBOUND),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(log)
        self.assertEqual(log.status, SYNC_STATUS_FAILED)
        self.assertIn("SAP server connection refused", log.error_message)

    @patch("requests.post")
    def test_03_webhook_manual_retry(self, mock_post):
        """REQ-WHK-02: Manual retry button resends webhook and updates sync status."""
        doc_num = f"PO-TEST-WHK-RETRY-{uuid.uuid4().hex[:6].upper()}"
        picking = self._create_assigned_picking(doc_num)

        # Step 1: Initial validation fails
        mock_post.side_effect = requests.exceptions.Timeout("Timeout connecting to SAP")
        for line in picking.move_line_ids:
            line.quantity = line.quantity_product_uom or 10
        picking.button_validate()
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_FAILED)

        # Step 2: Retry succeeds
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(
            {
                "status": "SUCCESS",
                "code": 200,
                "message": "Retry successful",
            }
        )
        mock_post.side_effect = None
        mock_post.return_value = mock_response

        res = picking.action_send_sap_goods_receipt_webhook()
        self.assertTrue(res)
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_SYNCED)
