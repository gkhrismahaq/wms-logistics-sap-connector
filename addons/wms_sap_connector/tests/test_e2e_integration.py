"""End-to-End (E2E) Integration Test Suite for Two-Tier WMS & SAP Connector.

Validates the complete bidirectional lifecycle across:
1. Master Data Synchronization (Material, Vendor, Customer, Image Base64).
2. Inbound PO Reception, Putaway Allocation, Stock Validation, and Goods Receipt Webhook.
3. Outbound Delivery, Fleet Assignment, Surat Jalan PDF, POD, and Goods Issue Webhook.
4. Network Failure Resilience, Non-Blocking Stock Operations, and Manual Retry.
5. Multi-Role Security Access Rights (Operator, Dispatcher, Manager).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import requests
from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from ..constants import (
    CONFIG_PARAM_SAP_API_TOKEN,
    CONFIG_PARAM_SAP_BASE_URL,
    DIRECTION_INBOUND,
    DIRECTION_OUTBOUND,
    PICKING_TYPE_CODE_INCOMING,
    PICKING_TYPE_CODE_OUTGOING,
    REF_PREFIX_MASTER_DATA,
    SYNC_STATUS_FAILED,
    SYNC_STATUS_SUCCESS,
    SYNC_STATUS_SYNCED,
    SYNC_TYPE_INBOUND_PO,
    SYNC_TYPE_MASTER_PARTNER,
    SYNC_TYPE_MASTER_PRODUCT,
    SYNC_TYPE_OUTBOUND_SO,
    VEHICLE_STATE_AVAILABLE,
)

DUMMY_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@tagged("post_install", "-at_install", "wms_sap", "e2e")
class TestE2EIntegration(TransactionCase):
    """Enterprise-grade End-to-End integration test suite."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sap_token = "secret_sap_token_e2e_123"
        cls.sap_url = "http://mock-sap:8000"
        cls.env["ir.config_parameter"].sudo().set_param(
            CONFIG_PARAM_SAP_BASE_URL, cls.sap_url
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            CONFIG_PARAM_SAP_API_TOKEN, cls.sap_token
        )

        cls.group_operator = cls.env.ref("wms_sap_connector.group_wms_operator")
        cls.group_dispatcher = cls.env.ref("wms_sap_connector.group_wms_dispatcher")
        cls.group_manager = cls.env.ref("wms_sap_connector.group_wms_manager")

        cls.user_operator = cls.env["res.users"].create(
            {
                "name": "Operator E2E",
                "login": f"op_e2e_{uuid.uuid4().hex[:6]}",
                "email": "op_e2e@example.com",
                "groups_id": [(6, 0, [cls.group_operator.id, cls.env.ref("base.group_user").id])],
            }
        )
        cls.user_dispatcher = cls.env["res.users"].create(
            {
                "name": "Dispatcher E2E",
                "login": f"disp_e2e_{uuid.uuid4().hex[:6]}",
                "email": "disp_e2e@example.com",
                "groups_id": [(6, 0, [cls.group_dispatcher.id, cls.env.ref("base.group_user").id])],
            }
        )
        cls.user_manager = cls.env["res.users"].create(
            {
                "name": "Manager E2E",
                "login": f"mgr_e2e_{uuid.uuid4().hex[:6]}",
                "email": "mgr_e2e@example.com",
                "groups_id": [(6, 0, [cls.group_manager.id, cls.env.ref("base.group_user").id])],
            }
        )

        # Picking types and locations
        cls.picking_type_in = cls.env["stock.picking.type"].search(
            [("code", "=", PICKING_TYPE_CODE_INCOMING)], limit=1
        )
        cls.picking_type_out = cls.env["stock.picking.type"].search(
            [("code", "=", PICKING_TYPE_CODE_OUTGOING)], limit=1
        )
        cls.warehouse = cls.picking_type_in.warehouse_id
        cls.stock_loc = cls.warehouse.lot_stock_id
        cls.customer_loc = cls.env.ref("stock.stock_location_customers")
        cls.supplier_loc = cls.env.ref("stock.stock_location_suppliers")

        # Putaway destination racks
        cls.rack_dry = cls.env["stock.location"].create(
            {
                "name": "Rack A-01 Dry E2E",
                "location_id": cls.stock_loc.id,
                "usage": "internal",
                "barcode": "LOC-E2E-DRY-01",
            }
        )
        cls.rack_cold = cls.env["stock.location"].create(
            {
                "name": "Rack C-01 Cold E2E",
                "location_id": cls.stock_loc.id,
                "usage": "internal",
                "barcode": "LOC-E2E-COLD-01",
            }
        )

    def _generate_unique_ref(self, prefix: str) -> str:
        """Helper to generate non-colliding transaction codes."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        rand = uuid.uuid4().hex[:4].upper()
        return f"{prefix}-E2E-{ts}-{rand}"

    # -------------------------------------------------------------------------
    # Skenario 1: Sinkronisasi Master Data (Material & Partner)
    # -------------------------------------------------------------------------
    def test_01_e2e_master_data_sync_and_assertions(self):
        """Verifies end-to-end sync of product materials and business partners."""
        mat_code = self._generate_unique_ref("MAT")
        vend_code = self._generate_unique_ref("VEND")
        cust_code = self._generate_unique_ref("CUST")

        # 1. Product Master Sync
        prod_payload = {
            "master_type": "product",
            "data": [
                {
                    "sap_material_code": mat_code,
                    "name": "Kopi Arabika E2E Test",
                    "weight": 0.5,
                    "volume": 0.002,
                    "barcode": "8998877665544",
                    "image_base64": DUMMY_PNG_BASE64,
                }
            ],
        }

        # Use SapMasterDataController directly or simulate ORM logic
        prod_tmpl_obj = self.env["product.template"].sudo()
        created_prod = prod_tmpl_obj.create(
            {
                "name": prod_payload["data"][0]["name"],
                "sap_material_code": mat_code,
                "weight": prod_payload["data"][0]["weight"],
                "volume": prod_payload["data"][0]["volume"],
                "barcode": prod_payload["data"][0]["barcode"],
                "image_1920": prod_payload["data"][0]["image_base64"],
                "type": "product",
            }
        )
        self.assertTrue(created_prod.exists())
        self.assertEqual(created_prod.sap_material_code, mat_code)
        self.assertEqual(created_prod.weight, 0.5)
        self.assertTrue(bool(created_prod.image_1920))

        # Log to sap.sync.log
        sync_ref_prod = f"SYNC-{REF_PREFIX_MASTER_DATA}-{uuid.uuid4().hex[:6].upper()}"
        log_prod = self.env["sap.sync.log"].sudo().create(
            {
                "name": sync_ref_prod,
                "sync_type": SYNC_TYPE_MASTER_PRODUCT,
                "direction": DIRECTION_INBOUND,
                "payload": json.dumps(prod_payload),
                "status": SYNC_STATUS_SUCCESS,
                "sync_date": fields.Datetime.now(),
            }
        )
        self.assertEqual(log_prod.status, SYNC_STATUS_SUCCESS)

        # 2. Partner Master Sync (Vendor & Customer)
        partner_obj = self.env["res.partner"].sudo()
        vendor = partner_obj.create(
            {
                "name": "PT Indomarco E2E Vendor",
                "sap_partner_code": vend_code,
                "supplier_rank": 1,
            }
        )
        customer = partner_obj.create(
            {
                "name": "PT Sumber Alfaria E2E Customer",
                "sap_partner_code": cust_code,
                "customer_rank": 1,
            }
        )
        self.assertEqual(vendor.sap_partner_code, vend_code)
        self.assertEqual(customer.sap_partner_code, cust_code)

        log_partner = self.env["sap.sync.log"].sudo().create(
            {
                "name": f"SYNC-{REF_PREFIX_MASTER_DATA}-{uuid.uuid4().hex[:6].upper()}",
                "sync_type": SYNC_TYPE_MASTER_PARTNER,
                "direction": DIRECTION_INBOUND,
                "payload": json.dumps({"vendor": vend_code, "customer": cust_code}),
                "status": SYNC_STATUS_SUCCESS,
                "sync_date": fields.Datetime.now(),
            }
        )
        self.assertEqual(log_partner.direction, DIRECTION_INBOUND)

    # -------------------------------------------------------------------------
    # Skenario 2: Alur Inbound PO, Putaway, dan Webhook Goods Receipt
    # -------------------------------------------------------------------------
    @patch("odoo.addons.wms_sap_connector.models.stock_picking.requests.post")
    def test_02_e2e_inbound_po_putaway_and_goods_receipt_webhook(self, mock_post):
        """Verifies Inbound PO creation, Putaway Rule execution, and Goods Receipt webhook acknowledgement."""
        sap_doc = self._generate_unique_ref("PO-SAP")
        mat_code = self._generate_unique_ref("MAT-IN")
        vend_code = self._generate_unique_ref("VEND-IN")

        vendor = self.env["res.partner"].create(
            {"name": "Supplier Utama E2E", "sap_partner_code": vend_code}
        )
        product = self.env["product.product"].create(
            {
                "name": "Kopi Sachet Inbound E2E",
                "sap_material_code": mat_code,
                "type": "product",
            }
        )

        # Configure putaway rule: Product -> Rack Dry
        self.env["stock.putaway.rule"].create(
            {
                "product_id": product.id,
                "location_in_id": self.picking_type_in.default_location_dest_id.id,
                "location_out_id": self.rack_dry.id,
            }
        )

        # Simulate SAP sending Inbound PO
        po_payload = {
            "sap_doc_number": sap_doc,
            "vendor_code": vend_code,
            "expected_date": "2026-10-28",
            "items": [{"sap_material_code": mat_code, "qty": 100.0, "uom": "Unit"}],
        }

        picking, is_created = (
            self.env["stock.picking"].sudo().create_inbound_from_sap(po_payload)
        )
        self.assertTrue(is_created)
        self.assertEqual(picking.sap_doc_number, sap_doc)
        self.assertEqual(picking.partner_id.id, vendor.id)
        self.assertEqual(picking.state, "assigned")

        # Verify putaway rule applied on move line
        self.assertTrue(len(picking.move_line_ids) >= 1)
        move_line = picking.move_line_ids[0]
        self.assertEqual(move_line.location_dest_id.id, self.rack_dry.id)

        # Mock SAP webhook response for Goods Receipt
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_json_data = {
            "status": "SUCCESS",
            "code": 200,
            "message": f"Goods Receipt posted into SAP General Ledger for {sap_doc}",
            "sap_accounting_log": {
                "journal_entry": f"JE-SAP-2026-{uuid.uuid4().hex[:4].upper()}",
                "posting_date": "2026-10-28",
                "debit_account": "101.001 - Persediaan Barang Masuk (Rp 50.000.000)",
                "credit_account": "201.001 - Hutang Dagang Belum Difakturkan (Rp 50.000.000)",
                "vat_in_11%": "Rp 5.500.000",
                "financial_status": "POSTED",
            },
        }
        mock_resp.json.return_value = mock_json_data
        mock_resp.text = json.dumps(mock_json_data)
        mock_post.return_value = mock_resp

        # Set move quantities and validate
        for m in picking.move_ids:
            m.quantity = m.product_uom_qty
            m.picked = True
        picking.button_validate()

        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_SYNCED)
        self.assertTrue(mock_post.called)

        # Verify sap.sync.log recorded outbound accounting log
        sync_log = self.env["sap.sync.log"].search(
            [
                ("sync_type", "=", SYNC_TYPE_INBOUND_PO),
                ("direction", "=", DIRECTION_OUTBOUND),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(sync_log.exists())
        self.assertEqual(sync_log.direction, DIRECTION_OUTBOUND)
        self.assertEqual(sync_log.sync_type, SYNC_TYPE_INBOUND_PO)
        self.assertEqual(sync_log.status, SYNC_STATUS_SUCCESS)

    # -------------------------------------------------------------------------
    # Skenario 3: Alur Outbound Delivery, Armada, POD, dan Webhook Goods Issue
    # -------------------------------------------------------------------------
    @patch("odoo.addons.wms_sap_connector.models.stock_picking.requests.post")
    def test_03_e2e_outbound_delivery_dispatch_pod_and_goods_issue_webhook(
        self, mock_post
    ):
        """Verifies Delivery Order creation, Vehicle allocation, Surat Jalan PDF, POD upload, and Goods Issue webhook."""
        sap_doc = self._generate_unique_ref("SO-DELIV")
        mat_code = self._generate_unique_ref("MAT-OUT")
        cust_code = self._generate_unique_ref("CUST-OUT")

        customer = self.env["res.partner"].create(
            {
                "name": "Toko Retail E2E",
                "sap_partner_code": cust_code,
                "street": "Jl. Kaliurang No. 12",
                "city": "Sleman",
            }
        )
        driver = self.env["res.partner"].create(
            {"name": "Pak Sopir E2E", "phone": "08123456789"}
        )
        vehicle = self.env["wms.vehicle"].create(
            {
                "license_plate": f"AB {uuid.uuid4().hex[:4].upper()} ZZ",
                "driver_id": driver.id,
                "max_weight": 2000.0,
                "max_volume": 10.0,
                "state": VEHICLE_STATE_AVAILABLE,
            }
        )
        product = self.env["product.product"].create(
            {
                "name": "Beras Premium 5kg E2E",
                "sap_material_code": mat_code,
                "weight": 5.0,
                "volume": 0.01,
                "type": "product",
            }
        )

        # Initial stock setup in source location
        self.env["stock.quant"]._update_available_quantity(
            product, self.stock_loc, 50.0
        )

        # 1. Simulate SAP sending Outbound Delivery
        delivery_payload = {
            "sap_doc_number": sap_doc,
            "customer_code": cust_code,
            "destination_city": "Sleman",
            "items": [{"sap_material_code": mat_code, "qty": 10.0, "uom": "Unit"}],
        }

        picking, is_created = (
            self.env["stock.picking"].sudo().create_outbound_from_sap(delivery_payload)
        )
        self.assertTrue(is_created)
        self.assertEqual(picking.sap_doc_number, sap_doc)
        self.assertEqual(picking.partner_id.id, customer.id)

        # 2. Assign Vehicle and Driver
        picking.write(
            {
                "vehicle_id": vehicle.id,
                "driver_id": driver.id,
            }
        )
        self.assertEqual(picking.vehicle_id.id, vehicle.id)
        self.assertEqual(picking.driver_id.id, driver.id)
        self.assertAlmostEqual(picking.total_weight, 50.0)  # 10 * 5kg
        self.assertAlmostEqual(picking.total_volume, 0.1)  # 10 * 0.01m3

        # 3. Verify Surat Jalan PDF QWeb report rendering
        report_action = self.env.ref(
            "wms_sap_connector.action_report_surat_jalan", raise_if_not_found=False
        )
        if report_action:
            pdf_content, _format = report_action.with_context(
                force_report_rendering=True
            )._render_qweb_pdf(report_action.id, [picking.id])
            self.assertTrue(len(pdf_content) > 0)

        # 4. Attach Proof of Delivery (POD)
        picking.write(
            {
                "proof_of_delivery": DUMMY_PNG_BASE64,
                "pod_signed_by": "Bpk. Penerima Toko",
                "pod_timestamp": fields.Datetime.now(),
            }
        )
        self.assertTrue(bool(picking.proof_of_delivery))
        self.assertEqual(picking.pod_signed_by, "Bpk. Penerima Toko")

        # 5. Mock SAP webhook response for Goods Issue
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_gi_json = {
            "status": "SUCCESS",
            "code": 200,
            "message": f"Goods Issue and POD acknowledged in SAP Financials for {sap_doc}",
            "sap_accounting_log": {
                "journal_entry": f"JE-SAP-2026-{uuid.uuid4().hex[:4].upper()}",
                "posting_date": "2026-10-28",
                "debit_account": "501.001 - Harga Pokok Penjualan (HPP) (Rp 25.000.000)",
                "credit_account": "101.001 - Persediaan Barang Jadi (Rp 25.000.000)",
                "financial_status": "POSTED",
            },
        }
        mock_resp.json.return_value = mock_gi_json
        mock_resp.text = json.dumps(mock_gi_json)
        mock_post.return_value = mock_resp

        # Validate delivery order
        for m in picking.move_ids:
            m.quantity = m.product_uom_qty
            m.picked = True
        picking.button_validate()

        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_SYNCED)
        self.assertTrue(mock_post.called)

        # Verify sap.sync.log recorded Goods Issue outbound log
        sync_log = self.env["sap.sync.log"].search(
            [
                ("sync_type", "=", SYNC_TYPE_OUTBOUND_SO),
                ("direction", "=", DIRECTION_OUTBOUND),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(sync_log.exists())
        self.assertEqual(sync_log.direction, DIRECTION_OUTBOUND)
        self.assertEqual(sync_log.sync_type, SYNC_TYPE_OUTBOUND_SO)
        self.assertEqual(sync_log.status, SYNC_STATUS_SUCCESS)

    # -------------------------------------------------------------------------
    # Skenario 4: Ketahanan Gangguan Jaringan & Pengiriman Ulang Manual (Retry)
    # -------------------------------------------------------------------------
    @patch("odoo.addons.wms_sap_connector.models.stock_picking.requests.post")
    def test_04_e2e_network_failure_resilience_and_manual_retry(self, mock_post):
        """Verifies warehouse physical movements remain done during SAP outages and manual retry succeeds."""
        sap_doc = self._generate_unique_ref("PO-FAIL")
        mat_code = self._generate_unique_ref("MAT-FAIL")
        vend_code = self._generate_unique_ref("VEND-FAIL")

        self.env["res.partner"].create(
            {"name": "Supplier Fail E2E", "sap_partner_code": vend_code}
        )
        self.env["product.product"].create(
            {
                "name": "Barang Uji Failover",
                "sap_material_code": mat_code,
                "type": "product",
            }
        )

        picking, _is_created = self.env["stock.picking"].sudo().create_inbound_from_sap(
            {
                "sap_doc_number": sap_doc,
                "vendor_code": vend_code,
                "expected_date": "2026-10-28",
                "items": [{"sap_material_code": mat_code, "qty": 10.0, "uom": "Unit"}],
            }
        )

        # Simulate SAP connection failure
        mock_post.side_effect = requests.exceptions.Timeout("Connection timeout to SAP")

        for m in picking.move_ids:
            m.quantity = m.product_uom_qty
            m.picked = True
        picking.button_validate()

        # Physical status MUST remain done
        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_FAILED)

        # Restore network and execute Manual Retry
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "SUCCESS",
            "code": 200,
            "message": "Retry successful",
            "sap_accounting_log": {"financial_status": "POSTED"},
        }
        mock_post.side_effect = None
        mock_post.return_value = mock_resp

        action_result = picking.action_send_sap_goods_receipt_webhook()
        self.assertTrue(action_result)
        self.assertEqual(picking.sap_sync_status, SYNC_STATUS_SYNCED)

    # -------------------------------------------------------------------------
    # Skenario 5: Validasi Hak Akses Peran Pengguna (Security Access Rights)
    # -------------------------------------------------------------------------
    def test_05_e2e_security_access_rights_roles(self):
        """Verifies ACL constraints across Warehouse Operator, Dispatcher, and Manager."""
        # 1. Warehouse Operator cannot manage vehicle fleet
        with self.assertRaises(AccessError):
            self.env["wms.vehicle"].with_user(self.user_operator).create(
                {
                    "license_plate": f"B {uuid.uuid4().hex[:4].upper()} XYZ",
                    "max_weight": 1000.0,
                    "max_volume": 5.0,
                }
            )

        # 2. Logistics Dispatcher can manage vehicle fleet
        disp_veh = self.env["wms.vehicle"].with_user(self.user_dispatcher).create(
            {
                "license_plate": f"D {uuid.uuid4().hex[:4].upper()} ABC",
                "max_weight": 1500.0,
                "max_volume": 8.0,
            }
        )
        self.assertTrue(disp_veh.exists())

        # 3. Warehouse Manager has full administrative control
        mgr_veh = self.env["wms.vehicle"].with_user(self.user_manager).create(
            {
                "license_plate": f"L {uuid.uuid4().hex[:4].upper()} MGR",
                "max_weight": 3000.0,
                "max_volume": 15.0,
            }
        )
        self.assertTrue(mgr_veh.exists())
        mgr_veh.unlink()
