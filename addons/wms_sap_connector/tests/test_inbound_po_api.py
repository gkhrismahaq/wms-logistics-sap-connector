# -*- coding: utf-8 -*-
import json
import uuid
from odoo.tests.common import HttpCase, tagged
from ..constants import (
    CONFIG_PARAM_SAP_API_TOKEN,
    HTTP_HEADER_API_KEY,
    SYNC_STATUS_SUCCESS,
    SYNC_TYPE_INBOUND_PO,
)


@tagged("post_install", "-at_install", "wms_sap")
class TestInboundPoApi(HttpCase):
    """Test suite for SAP Inbound Purchase Order REST API."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        configured_token = cls.env["ir.config_parameter"].sudo().get_param(
            CONFIG_PARAM_SAP_API_TOKEN
        )
        if not configured_token:
            configured_token = "secret_sap_token_123"
            cls.env["ir.config_parameter"].sudo().set_param(
                CONFIG_PARAM_SAP_API_TOKEN, configured_token
            )
        cls.token = configured_token

        cls.vendor = cls.env["res.partner"].sudo().search(
            [("sap_partner_code", "=", "VEND-INDOMARCO")], limit=1
        )
        if not cls.vendor:
            cls.vendor = cls.env["res.partner"].sudo().create({
                "name": "Test Vendor PT",
                "sap_partner_code": "VEND-INDOMARCO",
                "supplier_rank": 1,
            })

        cls.product = cls.env["product.product"].sudo().search(
            [("sap_material_code", "=", "MAT-KOPI-01")], limit=1
        )
        if not cls.product:
            cls.product = cls.env["product.product"].sudo().create({
                "name": "Test Inbound Product",
                "sap_material_code": "MAT-KOPI-01",
                "type": "product",
            })
        cls.cr.commit()

    def test_01_unauthorized_access(self):
        """API must reject requests without valid authentication token."""
        payload = {"sap_doc_number": "PO-TEST-UNAUTH-01"}
        response = self.url_open(
            "/api/sap/inbound/po",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 401)
        res_data = response.json()
        self.assertEqual(res_data.get("status"), "ERROR")
        self.assertEqual(res_data.get("code"), 401)

    def test_02_bad_request_missing_mandatory_fields(self):
        """API must reject payloads missing mandatory attributes."""
        headers = {
            "Content-Type": "application/json",
            HTTP_HEADER_API_KEY: self.token,
        }
        payload = {"sap_doc_number": "PO-TEST-MISSING-01"}
        response = self.url_open(
            "/api/sap/inbound/po",
            data=json.dumps(payload),
            headers=headers,
        )
        self.assertEqual(response.status_code, 400)
        res_data = response.json()
        self.assertEqual(res_data.get("status"), "ERROR")
        self.assertIn("Missing or invalid mandatory field", res_data.get("message", ""))

    def test_03_bad_request_unknown_vendor(self):
        """API must reject PO with unregistered vendor code."""
        headers = {
            "Content-Type": "application/json",
            HTTP_HEADER_API_KEY: self.token,
        }
        payload = {
            "sap_doc_number": "PO-TEST-NOVENDOR-01",
            "vendor_code": "VEND-NONEXISTENT-999",
            "items": [{"sap_material_code": self.product.sap_material_code, "qty": 10.0}],
        }
        response = self.url_open(
            "/api/sap/inbound/po",
            data=json.dumps(payload),
            headers=headers,
        )
        self.assertEqual(response.status_code, 400)
        res_data = response.json()
        self.assertEqual(res_data.get("status"), "ERROR")
        self.assertIn("not found", res_data.get("message", ""))

    def test_04_bad_request_unknown_material(self):
        """API must reject PO with unregistered material code."""
        headers = {
            "Content-Type": "application/json",
            HTTP_HEADER_API_KEY: self.token,
        }
        payload = {
            "sap_doc_number": "PO-TEST-NOMAT-01",
            "vendor_code": self.vendor.sap_partner_code,
            "items": [{"sap_material_code": "MAT-NONEXISTENT-999", "qty": 10.0}],
        }
        response = self.url_open(
            "/api/sap/inbound/po",
            data=json.dumps(payload),
            headers=headers,
        )
        self.assertEqual(response.status_code, 400)
        res_data = response.json()
        self.assertEqual(res_data.get("status"), "ERROR")
        self.assertIn("not found", res_data.get("message", ""))

    def test_05_successful_po_creation_and_idempotency(self):
        """API must create picking with 'assigned' state and respond idempotently on repeat."""
        headers = {
            "Content-Type": "application/json",
            HTTP_HEADER_API_KEY: self.token,
        }
        doc_number = f"PO-TEST-IDEMPOTENT-{uuid.uuid4().hex[:6].upper()}"
        payload = {
            "sap_doc_number": doc_number,
            "vendor_code": self.vendor.sap_partner_code,
            "expected_date": "2026-11-01",
            "items": [
                {
                    "sap_material_code": self.product.sap_material_code,
                    "qty": 50.0,
                    "uom": self.product.uom_id.name,
                }
            ],
        }

        # First Call: Created (201)
        response_1 = self.url_open(
            "/api/sap/inbound/po",
            data=json.dumps(payload),
            headers=headers,
        )
        self.assertEqual(response_1.status_code, 201)
        res_1 = response_1.json()
        self.assertEqual(res_1.get("status"), "SUCCESS")
        self.assertEqual(res_1.get("code"), 201)
        self.assertEqual(res_1.get("state"), "assigned")
        picking_id = res_1.get("odoo_picking_id")
        self.assertTrue(picking_id)

        # Verify record in database using isolated cursor
        with self.registry.cursor() as new_cr:
            env = self.env(cr=new_cr)
            picking = env["stock.picking"].browse(picking_id)
            self.assertTrue(picking.exists())
            self.assertEqual(picking.sap_doc_number, doc_number)
            self.assertEqual(picking.state, "assigned")
            self.assertEqual(len(picking.move_ids), 1)
            self.assertEqual(picking.move_ids[0].product_uom_qty, 50.0)

        # Second Call: Idempotent (200)
        response_2 = self.url_open(
            "/api/sap/inbound/po",
            data=json.dumps(payload),
            headers=headers,
        )
        self.assertEqual(response_2.status_code, 200)
        res_2 = response_2.json()
        self.assertEqual(res_2.get("status"), "SUCCESS")
        self.assertEqual(res_2.get("code"), 200)
        self.assertEqual(res_2.get("odoo_picking_id"), picking_id)
        self.assertIn("idempotent", res_2.get("message", "").lower())

        # Verify audit log was recorded
        with self.registry.cursor() as new_cr:
            env = self.env(cr=new_cr)
            sync_log = env["sap.sync.log"].search(
                [("sync_type", "=", SYNC_TYPE_INBOUND_PO), ("status", "=", SYNC_STATUS_SUCCESS)],
                order="id desc",
                limit=1,
            )
            self.assertTrue(sync_log.exists())
            self.assertIn(doc_number, sync_log.payload)
