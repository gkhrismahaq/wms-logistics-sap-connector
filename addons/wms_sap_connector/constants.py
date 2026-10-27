"""Constants and enumerations for WMS SAP Connector."""

CONFIG_PARAM_SAP_BASE_URL = "wms_sap_connector.sap_base_url"
CONFIG_PARAM_SAP_API_TOKEN = "wms_sap_connector.sap_api_token"

HTTP_HEADER_API_KEY = "X-Odoo-API-Key"
HTTP_HEADER_AUTHORIZATION = "Authorization"
HTTP_HEADER_CONTENT_TYPE = "Content-Type"
HTTP_MIME_JSON = "application/json"
AUTH_BEARER_PREFIX = "Bearer "

HTTP_STATUS_OK = 200
HTTP_STATUS_CREATED = 201
HTTP_STATUS_BAD_REQUEST = 400
HTTP_STATUS_UNAUTHORIZED = 401
HTTP_STATUS_NOT_FOUND = 404
HTTP_STATUS_BAD_GATEWAY = 502

SYNC_STATUS_DRAFT = "draft"
SYNC_STATUS_PENDING = "pending"
SYNC_STATUS_SYNCED = "synced"
SYNC_STATUS_SUCCESS = "success"
SYNC_STATUS_FAILED = "failed"

SAP_PICKING_SYNC_STATUS_SELECTION = [
    (SYNC_STATUS_DRAFT, "Draft / Not Synced"),
    (SYNC_STATUS_PENDING, "Pending Sync"),
    (SYNC_STATUS_SYNCED, "Synced to SAP"),
    (SYNC_STATUS_FAILED, "Sync Failed"),
]

SAP_SYNC_LOG_STATUS_SELECTION = [
    (SYNC_STATUS_PENDING, "Pending"),
    (SYNC_STATUS_SUCCESS, "Success"),
    (SYNC_STATUS_FAILED, "Failed"),
]

SYNC_TYPE_MASTER_PRODUCT = "master_product"
SYNC_TYPE_MASTER_PARTNER = "master_partner"
SYNC_TYPE_MASTER_PLANT = "master_plant"
SYNC_TYPE_INBOUND_PO = "inbound_po"
SYNC_TYPE_OUTBOUND_SO = "outbound_so"

SAP_SYNC_TYPE_SELECTION = [
    (SYNC_TYPE_MASTER_PRODUCT, "Master Product / Material"),
    (SYNC_TYPE_MASTER_PARTNER, "Master Partner / Vendor / Customer"),
    (SYNC_TYPE_MASTER_PLANT, "Master Plant / Facility Location"),
    (SYNC_TYPE_INBOUND_PO, "Inbound Purchase Order"),
    (SYNC_TYPE_OUTBOUND_SO, "Outbound Sales Delivery"),
]

ALLOWED_SYNC_TYPES = (
    SYNC_TYPE_MASTER_PRODUCT,
    SYNC_TYPE_MASTER_PARTNER,
    SYNC_TYPE_MASTER_PLANT,
    SYNC_TYPE_INBOUND_PO,
    SYNC_TYPE_OUTBOUND_SO,
)

DIRECTION_INBOUND = "inbound"
DIRECTION_OUTBOUND = "outbound"

SAP_DIRECTION_SELECTION = [
    (DIRECTION_INBOUND, "Inbound (SAP -> Odoo)"),
    (DIRECTION_OUTBOUND, "Outbound (Odoo -> SAP)"),
]

MASTER_TYPE_PRODUCT = "product"
MASTER_TYPE_PARTNER = "partner"
MASTER_TYPE_PLANT = "plant"

PARTNER_TYPE_VENDOR = "vendor"
PARTNER_TYPE_CUSTOMER = "customer"

PRODUCT_TYPE_STORABLE = "product"

REF_PREFIX_MASTER_DATA = "MD"
REF_PREFIX_INBOUND_PO = "PO"
REF_PREFIX_OUTBOUND_SO = "SO"
REF_PREFIX_GOODS_RECEIPT = "GR"
REF_PREFIX_GOODS_ISSUE = "GI"

SAP_ENDPOINT_GOODS_RECEIPT = "/api/sap/goods-receipt"
SAP_ENDPOINT_GOODS_ISSUE = "/api/sap/goods-issue"
WEBHOOK_STATUS_GOODS_RECEIVED = "GOODS_RECEIVED"
WEBHOOK_STATUS_GOODS_ISSUED = "GOODS_ISSUED"
WEBHOOK_TIMEOUT_SECONDS = 10

PICKING_TYPE_CODE_INCOMING = "incoming"
PICKING_TYPE_CODE_OUTGOING = "outgoing"
PICKING_TYPE_CODE_INTERNAL = "internal"

PICKING_STATE_DRAFT = "draft"
PICKING_STATE_CONFIRMED = "confirmed"
PICKING_STATE_ASSIGNED = "assigned"
PICKING_STATE_DONE = "done"
PICKING_STATE_CANCEL = "cancel"

ERROR_UNAUTHORIZED = "Unauthorized: Invalid or missing API token"
ERROR_INVALID_JSON = "Bad Request: Invalid JSON body"
DEFAULT_RECEIVER_NAME = "Penerima Kargo"

ERR_MISSING_DOC_NUMBER = (
    "Bad Request: Missing or invalid mandatory field 'sap_doc_number'"
)
ERR_MISSING_VENDOR_CODE = (
    "Bad Request: Missing or invalid mandatory field 'vendor_code'"
)
ERR_MISSING_CUSTOMER_CODE = (
    "Bad Request: Missing or invalid mandatory field 'customer_code'"
)
ERR_EMPTY_ITEMS = "Bad Request: Missing or empty 'items' array"
ERR_SAP_BASE_URL_NOT_SET = "SAP Base URL not configured in system settings."
ERR_MISSING_MASTER_TYPE_OR_DATA = (
    "Bad Request: Missing 'master_type' or empty 'data' payload"
)
ERR_OPERATION_TYPE_NOT_CONFIGURED = (
    "Operation type (stock.picking.type) not configured in the system."
)
ERR_SRC_LOCATION_NOT_CONFIGURED = "Source stock location not configured."
ERR_DEST_LOCATION_NOT_CONFIGURED = "Destination location not configured."
ERR_DUPLICATE_LICENSE_PLATE = "Nomor plat polisi kendaraan harus unik!"
ERR_DUPLICATE_MATERIAL_CODE = "SAP Material Code must be unique across all products!"
ERR_DUPLICATE_PARTNER_CODE = "SAP Partner Code must be unique across all partners!"
ERR_DUPLICATE_SAP_DOC_NUMBER = "The SAP document number must be unique per company."
ERR_MATERIAL_NOT_FOUND = "Material with SAP material code '{code}' not found"
ERR_QTY_MUST_BE_POSITIVE = "must be greater than 0"
ERR_ONLY_MANAGER_CAN_DELETE_PICKING = (
    "Hanya Warehouse Manager yang memiliki wewenang untuk menghapus dokumen transfer logistik!"
)
ERR_CANNOT_DELETE_SAP_PICKING = (
    "Dokumen transfer yang terintegrasi dengan SAP (%s) tidak boleh dihapus!"
)
ERR_CANNOT_DELETE_DONE_PICKING = (
    "Dokumen transfer logistik yang sudah selesai (Done) tidak boleh dihapus!"
)
ERR_ONLY_DISPATCHER_CAN_ASSIGN_FLEET = (
    "Hanya Logistics Dispatcher atau Warehouse Manager yang berwenang menetapkan armada kendaraan dan supir!"
)
ERR_ONLY_DISPATCHER_CAN_MANAGE_POD = (
    "Hanya Logistics Dispatcher atau Warehouse Manager yang berwenang mengunggah bukti serah terima (POD)!"
)
ERR_ONLY_MANAGER_CAN_RETRY_SYNC = (
    "Hanya Warehouse Manager yang berwenang melakukan pengiriman ulang (retry) sinkronisasi SAP!"
)
ERR_ONLY_DISPATCHER_CAN_PRINT_SURAT_JALAN = (
    "Hanya Logistics Dispatcher atau Warehouse Manager yang berwenang mencetak dokumen Surat Jalan!"
)

GROUP_WMS_OPERATOR = "wms_sap_connector.group_wms_operator"
GROUP_WMS_DISPATCHER = "wms_sap_connector.group_wms_dispatcher"
GROUP_WMS_MANAGER = "wms_sap_connector.group_wms_manager"

VEHICLE_STATE_AVAILABLE = "available"
VEHICLE_STATE_ON_DELIVERY = "on_delivery"
VEHICLE_STATE_MAINTENANCE = "maintenance"

VEHICLE_STATE_SELECTION = [
    (VEHICLE_STATE_AVAILABLE, "Tersedia / Siap Jalan"),
    (VEHICLE_STATE_ON_DELIVERY, "Sedang Bertugas / Pengantaran"),
    (VEHICLE_STATE_MAINTENANCE, "Perawatan / Bengkel"),
]

FLOAT_DIGITS_CAPACITY = (12, 2)
FLOAT_DIGITS_VOLUME = (12, 4)
DEFAULT_VEHICLE_CAPACITY = 0.0

DATE_FMT_COMPACT = "%Y%m%d"
DATE_FMT_ISO_UTC = "%Y-%m-%dT%H:%M:%SZ"
DATE_FMT_DATE_ONLY = "%Y-%m-%d"

MAX_IMAGE_SIZE_BYTES = 2 * 1024 * 1024
IMAGE_DIMENSIONS_STANDARD = (1920, 1920)
IMAGE_QUALITY_STANDARD = 85
