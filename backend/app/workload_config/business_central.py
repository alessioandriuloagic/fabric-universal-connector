"""
Workload config: Business Central
Source: Dynamics 365 Business Central OData v4
Entities: standard BC REST API v2.0 endpoints (all companies-scoped entities)

Entity field semantics:
  api_endpoint  — OData endpoint segment (e.g. "customers")
  display_name  — human-readable label for the UI
  bronze_table  — Delta table path under the Bronze Lakehouse
"""
from __future__ import annotations

WORKLOAD_METADATA = {
    "id": "business-central",
    "display_name": "Business Central",
    "source": "businesscentral",
    "entities": [
        {
            "api_endpoint": "customers",
            "display_name": "Customer",
            "bronze_table": "bronze_bc/customers",
        },
        {
            "api_endpoint": "vendors",
            "display_name": "Vendor",
            "bronze_table": "bronze_bc/vendors",
        },
        {
            "api_endpoint": "items",
            "display_name": "Item",
            "bronze_table": "bronze_bc/items",
        },
        {
            "api_endpoint": "salesOrders",
            "display_name": "Sales Order",
            "bronze_table": "bronze_bc/salesOrders",
        },
        {
            "api_endpoint": "salesOrderLines",
            "display_name": "Sales Order Line",
            "bronze_table": "bronze_bc/salesOrderLines",
        },
        {
            "api_endpoint": "salesInvoices",
            "display_name": "Sales Invoice",
            "bronze_table": "bronze_bc/salesInvoices",
        },
        {
            "api_endpoint": "salesInvoiceLines",
            "display_name": "Sales Invoice Line",
            "bronze_table": "bronze_bc/salesInvoiceLines",
        },
        {
            "api_endpoint": "purchaseOrders",
            "display_name": "Purchase Order",
            "bronze_table": "bronze_bc/purchaseOrders",
        },
        {
            "api_endpoint": "purchaseOrderLines",
            "display_name": "Purchase Order Line",
            "bronze_table": "bronze_bc/purchaseOrderLines",
        },
        {
            "api_endpoint": "purchaseInvoices",
            "display_name": "Purchase Invoice",
            "bronze_table": "bronze_bc/purchaseInvoices",
        },
        {
            "api_endpoint": "generalLedgerEntries",
            "display_name": "General Ledger Entry",
            "bronze_table": "bronze_bc/generalLedgerEntries",
        },
        {
            "api_endpoint": "accounts",
            "display_name": "Account (Chart of Accounts)",
            "bronze_table": "bronze_bc/accounts",
        },
        {
            "api_endpoint": "employees",
            "display_name": "Employee",
            "bronze_table": "bronze_bc/employees",
        },
        {
            "api_endpoint": "contacts",
            "display_name": "Contact",
            "bronze_table": "bronze_bc/contacts",
        },
    ],
}

ALLOWED_ENTITY_NAMES: frozenset[str] = frozenset(
    e["api_endpoint"] for e in WORKLOAD_METADATA["entities"]
)
