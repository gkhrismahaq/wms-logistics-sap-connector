import json
import uuid

from odoo.tests.common import HttpCase, tagged

from ..constants import (
    AUTH_BEARER_PREFIX,
    CONFIG_PARAM_SAP_API_TOKEN,
    DIRECTION_INBOUND,
    HTTP_HEADER_API_KEY,
    HTTP_HEADER_AUTHORIZATION,
    PICKING_TYPE_CODE_OUTGOING,
    SYNC_STATUS_FAILED,
    SYNC_STATUS_SUCCESS,
    SYNC_TYPE_OUTBOUND_SO,
)


@tagged("post_install", "-at_install", "wms_sap")
class TestOutboundDeliveryApi(HttpCase):
    """Test suite for SAP Outbound Delivery Order REST API (POST /api/sap/outbound/delivery)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        configured_token = (
            cls.env["ir.config_parameter"].sudo().get_param(CONFIG_PARAM_SAP_API_TOKEN)
        )
        if not configured_token:
            configured_token = "secret_sap_token_outbound_123"
            cls.env["ir.config_parameter"].sudo().set_param(
                CONFIG_PARAM_SAP_API_TOKEN, configured_token
            )
        cls.token = configured_token

        cls.customer = (
            cls.env["res.partner"]
            .sudo()
            .search([("sap_partner_code", "=", "CUST-ALFAMART-01")], limit=1)
        )
        if not cls.customer:
            cls.customer = (
                cls.env["res.partner"]
                .sudo()
                .create(
                    {
                        "name": "PT Sumber Alfaria Trijaya",
                        "sap_partner_code": "CUST-ALFAMART-01",
                        "customer_rank": 1,
                    }
                )
            )

        tmpl_1 = (
            cls.env["product.template"]
            .sudo()
            .with_context(active_test=False)
            .search([("sap_material_code", "=", "MAT-KOPI-01")], limit=1)
        )
        if tmpl_1:
            tmpl_1.active = True
            tmpl_1.with_context(active_test=False).product_variant_ids.write({"active": True})
            cls.product_1 = tmpl_1.product_variant_id
        else:
            cls.product_1 = (
                cls.env["product.product"]
                .sudo()
                .create(
                    {
                        "name": "Kopi Kapal Api Special 165g",
                        "sap_material_code": "MAT-KOPI-01",
                        "type": "product",
                    }
                )
            )

        tmpl_2 = (
            cls.env["product.template"]
            .sudo()
            .with_context(active_test=False)
            .search([("sap_material_code", "=", "MAT-TEH-02")], limit=1)
        )
        if tmpl_2:
            tmpl_2.active = True
            tmpl_2.with_context(active_test=False).product_variant_ids.write({"active": True})
            cls.product_2 = tmpl_2.product_variant_id
        else:
            cls.product_2 = (
                cls.env["product.product"]
                .sudo()
                .create(
                    {
                        "name": "Teh Celup Sariwangi 25s",
                        "sap_material_code": "MAT-TEH-02",
                        "type": "product",
                    }
                )
            )

        cls.cr.commit()

    def test_01_unauthorized_access(self):
        """API must reject requests without valid authentication token and record failed audit log."""
        payload = {"sap_doc_number": "SO-DELIV-UNAUTH-01"}
        response = self.url_open(
            "/api/sap/outbound/delivery",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 401)
        res_data = response.json()
        self.assertEqual(res_data.get("status"), "ERROR")
        self.assertEqual(res_data.get("code"), 401)
        self.assertIn("Unauthorized", res_data.get("message", ""))

        # Invalid token in X-Odoo-API-Key
        response_bad_key = self.url_open(
            "/api/sap/outbound/delivery",
            data=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                HTTP_HEADER_API_KEY: "wrong_token",
            },
        )
        self.assertEqual(response_bad_key.status_code, 401)

        # Verify failed audit log
        with self.registry.cursor() as new_cr:
            env = self.env(cr=new_cr)
            failed_log = env["sap.sync.log"].search(
                [
                    ("sync_type", "=", SYNC_TYPE_OUTBOUND_SO),
                    ("status", "=", SYNC_STATUS_FAILED),
                    ("direction", "=", DIRECTION_INBOUND),
                ],
                order="id desc",
                limit=1,
            )
            self.assertTrue(failed_log.exists())
            self.assertIn("Unauthorized", failed_log.error_message)

    def test_02_bad_request_missing_mandatory_fields(self):
        """API must reject payloads missing mandatory attributes with HTTP 400."""
        headers = {
            "Content-Type": "application/json",
            HTTP_HEADER_API_KEY: self.token,
        }

        # Missing customer_code and items
        payload_1 = {"sap_doc_number": "SO-TEST-MISSING-01"}
        response_1 = self.url_open(
            "/api/sap/outbound/delivery",
            data=json.dumps(payload_1),
            headers=headers,
        )
        self.assertEqual(response_1.status_code, 400)
        res_1 = response_1.json()
        self.assertEqual(res_1.get("status"), "ERROR")
        self.assertIn("Missing or invalid mandatory field", res_1.get("message", ""))

        # Missing sap_doc_number
        payload_2 = {
            "customer_code": self.customer.sap_partner_code,
            "items": [
                {"sap_material_code": self.product_1.sap_material_code, "qty": 10}
            ],
        }
        response_2 = self.url_open(
            "/api/sap/outbound/delivery",
            data=json.dumps(payload_2),
            headers=headers,
        )
        self.assertEqual(response_2.status_code, 400)
        res_2 = response_2.json()
        self.assertEqual(res_2.get("status"), "ERROR")
        self.assertIn("sap_doc_number", res_2.get("message", ""))

        # Empty items array
        payload_3 = {
            "sap_doc_number": "SO-TEST-EMPTY-ITEMS-01",
            "customer_code": self.customer.sap_partner_code,
            "items": [],
        }
        response_3 = self.url_open(
            "/api/sap/outbound/delivery",
            data=json.dumps(payload_3),
            headers=headers,
        )
        self.assertEqual(response_3.status_code, 400)
        res_3 = response_3.json()
        self.assertEqual(res_3.get("status"), "ERROR")
        self.assertIn("Missing or empty 'items' array", res_3.get("message", ""))

        # Invalid qty (<= 0)
        payload_4 = {
            "sap_doc_number": "SO-TEST-INVALID-QTY-01",
            "customer_code": self.customer.sap_partner_code,
            "items": [
                {"sap_material_code": self.product_1.sap_material_code, "qty": -5}
            ],
        }
        response_4 = self.url_open(
            "/api/sap/outbound/delivery",
            data=json.dumps(payload_4),
            headers=headers,
        )
        self.assertEqual(response_4.status_code, 400)
        res_4 = response_4.json()
        self.assertEqual(res_4.get("status"), "ERROR")
        self.assertIn("must be greater than 0", res_4.get("message", ""))

    def test_03_bad_request_unknown_customer(self):
        """API must reject delivery order with unregistered customer code."""
        headers = {
            "Content-Type": "application/json",
            HTTP_HEADER_API_KEY: self.token,
        }
        payload = {
            "sap_doc_number": "SO-TEST-NOCUST-01",
            "customer_code": "CUST-NONEXISTENT-999",
            "items": [
                {"sap_material_code": self.product_1.sap_material_code, "qty": 10.0}
            ],
        }
        response = self.url_open(
            "/api/sap/outbound/delivery",
            data=json.dumps(payload),
            headers=headers,
        )
        self.assertEqual(response.status_code, 400)
        res_data = response.json()
        self.assertEqual(res_data.get("status"), "ERROR")
        self.assertIn(
            "Customer with SAP partner code 'CUST-NONEXISTENT-999' not found",
            res_data.get("message", ""),
        )

    def test_04_bad_request_unknown_material(self):
        """API must reject delivery order with unregistered material code."""
        headers = {
            "Content-Type": "application/json",
            HTTP_HEADER_API_KEY: self.token,
        }
        payload = {
            "sap_doc_number": "SO-TEST-NOMAT-01",
            "customer_code": self.customer.sap_partner_code,
            "items": [{"sap_material_code": "MAT-NONEXISTENT-999", "qty": 10.0}],
        }
        response = self.url_open(
            "/api/sap/outbound/delivery",
            data=json.dumps(payload),
            headers=headers,
        )
        self.assertEqual(response.status_code, 400)
        res_data = response.json()
        self.assertEqual(res_data.get("status"), "ERROR")
        self.assertIn(
            "Material with SAP material code 'MAT-NONEXISTENT-999' not found",
            res_data.get("message", ""),
        )

    def test_05_successful_outbound_delivery_creation_and_idempotency(self):
        """API must create outgoing picking and respond idempotently on repeat requests."""
        headers = {
            "Content-Type": "application/json",
            HTTP_HEADER_API_KEY: self.token,
        }
        doc_number = f"SO-DELIV-2026-{uuid.uuid4().hex[:6].upper()}"
        payload = {
            "sap_doc_number": doc_number,
            "customer_code": self.customer.sap_partner_code,
            "destination_city": "Jakarta Barat",
            "expected_date": "2026-11-15T08:00:00Z",
            "items": [
                {
                    "sap_material_code": self.product_1.sap_material_code,
                    "qty": 40.0,
                    "uom": self.product_1.uom_id.name,
                },
                {
                    "sap_material_code": self.product_2.sap_material_code,
                    "qty": 20.0,
                    "uom": self.product_2.uom_id.name,
                },
            ],
        }

        # First Call: Created (HTTP 200)
        response_1 = self.url_open(
            "/api/sap/outbound/delivery",
            data=json.dumps(payload),
            headers=headers,
        )
        self.assertEqual(response_1.status_code, 200)
        res_1 = response_1.json()
        self.assertEqual(res_1.get("status"), "SUCCESS")
        self.assertEqual(res_1.get("code"), 200)
        self.assertEqual(res_1.get("message"), "Delivery Order created successfully")
        self.assertEqual(res_1.get("sap_doc_number"), doc_number)
        self.assertTrue(res_1.get("sync_ref", "").startswith("SYNC-SO-"))
        picking_id = res_1.get("picking_id")
        self.assertTrue(picking_id)
        picking_name = res_1.get("picking_name")
        self.assertTrue(picking_name)

        # Verify record in database using isolated cursor
        with self.registry.cursor() as new_cr:
            env = self.env(cr=new_cr)
            picking = env["stock.picking"].browse(picking_id)
            self.assertTrue(picking.exists())
            self.assertEqual(picking.sap_doc_number, doc_number)
            self.assertEqual(picking.picking_type_id.code, PICKING_TYPE_CODE_OUTGOING)
            self.assertEqual(picking.partner_id.id, self.customer.id)
            self.assertEqual(picking.origin, doc_number)
            self.assertEqual(len(picking.move_ids), 2)
            self.assertIn(picking.state, ("confirmed", "assigned"))

            move_qtys = {
                m.product_id.sap_material_code: m.product_uom_qty
                for m in picking.move_ids
            }
            self.assertEqual(move_qtys.get("MAT-KOPI-01"), 40.0)
            self.assertEqual(move_qtys.get("MAT-TEH-02"), 20.0)

        # Second Call: Idempotent (HTTP 200)
        response_2 = self.url_open(
            "/api/sap/outbound/delivery",
            data=json.dumps(payload),
            headers=headers,
        )
        self.assertEqual(response_2.status_code, 200)
        res_2 = response_2.json()
        self.assertEqual(res_2.get("status"), "SUCCESS")
        self.assertEqual(res_2.get("code"), 200)
        self.assertEqual(
            res_2.get("message"), "Delivery Order already exists (idempotent)"
        )
        self.assertEqual(res_2.get("picking_id"), picking_id)
        self.assertEqual(res_2.get("picking_name"), picking_name)

        # Verify no duplicate pickings created
        with self.registry.cursor() as new_cr:
            env = self.env(cr=new_cr)
            pickings = env["stock.picking"].search(
                [("sap_doc_number", "=", doc_number)]
            )
            self.assertEqual(len(pickings), 1)

            # Verify audit log was recorded for outbound_so
            sync_log = env["sap.sync.log"].search(
                [
                    ("sync_type", "=", SYNC_TYPE_OUTBOUND_SO),
                    ("status", "=", SYNC_STATUS_SUCCESS),
                    ("direction", "=", DIRECTION_INBOUND),
                ],
                order="id desc",
                limit=1,
            )
            self.assertTrue(sync_log.exists())
            self.assertIn(doc_number, sync_log.payload)

    def test_06_bearer_token_authentication(self):
        """API must accept valid authentication token via Authorization: Bearer <token> header."""
        headers = {
            "Content-Type": "application/json",
            HTTP_HEADER_AUTHORIZATION: f"{AUTH_BEARER_PREFIX}{self.token}",
        }
        doc_number = f"SO-DELIV-BEARER-{uuid.uuid4().hex[:6].upper()}"
        payload = {
            "sap_doc_number": doc_number,
            "customer_code": self.customer.sap_partner_code,
            "items": [
                {
                    "sap_material_code": self.product_1.sap_material_code,
                    "qty": 15.0,
                }
            ],
        }

        response = self.url_open(
            "/api/sap/outbound/delivery",
            data=json.dumps(payload),
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data.get("status"), "SUCCESS")
        self.assertEqual(res_data.get("picking_id"), res_data.get("picking_id"))
