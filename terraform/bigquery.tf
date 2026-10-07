# ==============================================================================
# 2. BigQuery FSI Fraud & AML Dataset, Tables & Seed Job (Southbound MCP Target)
# ==============================================================================

resource "google_bigquery_dataset" "fsi_fraud_demo" {
  project                    = var.project_id
  dataset_id                 = var.bq_dataset_id
  friendly_name              = "Enterprise FSI Fraud & AML Dataset (BigQuery MCP)"
  description                = "Queried exclusively via Apigee X Proxy 5 (bigquery-mcp-gateway -> /v1/mcp/bigquery) using MCP execute_sql_readonly."
  location                   = var.bq_location
  delete_contents_on_destroy = true

  labels = {
    datacloud       = "jetski"
    vertical        = "fsi-aml-demo"
    goog-mcp-server = "true"
  }

  depends_on = [google_project_service.enabled_apis]
}

resource "google_bigquery_table" "customer_portfolios" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.fsi_fraud_demo.dataset_id
  table_id            = "customer_portfolios"
  deletion_protection = false

  schema = jsonencode([
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "customer_name", type = "STRING", mode = "NULLABLE" },
    { name = "segment", type = "STRING", mode = "NULLABLE" },
    { name = "kyc_status", type = "STRING", mode = "NULLABLE" },
    { name = "pep_flag", type = "BOOL", mode = "NULLABLE" },
    { name = "aml_risk_tier", type = "STRING", mode = "NULLABLE" },
    { name = "aum_eur", type = "FLOAT64", mode = "NULLABLE" },
    { name = "credit_exposure_eur", type = "FLOAT64", mode = "NULLABLE" },
    { name = "sanctions_screening", type = "STRING", mode = "NULLABLE" },
    { name = "relationship_manager", type = "STRING", mode = "NULLABLE" },
    { name = "country_residence", type = "STRING", mode = "NULLABLE" },
    { name = "onboarding_date", type = "DATE", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "transactions_ledger" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.fsi_fraud_demo.dataset_id
  table_id            = "transactions_ledger"
  deletion_protection = false

  schema = jsonencode([
    { name = "tx_id", type = "STRING", mode = "REQUIRED" },
    { name = "tx_timestamp", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "customer_id", type = "STRING", mode = "NULLABLE" },
    { name = "account_iban", type = "STRING", mode = "NULLABLE" },
    { name = "merchant_name", type = "STRING", mode = "NULLABLE" },
    { name = "merchant_category", type = "STRING", mode = "NULLABLE" },
    { name = "country_code", type = "STRING", mode = "NULLABLE" },
    { name = "channel", type = "STRING", mode = "NULLABLE" },
    { name = "amount_eur", type = "FLOAT64", mode = "NULLABLE" },
    { name = "risk_score", type = "INT64", mode = "NULLABLE" },
    { name = "anomaly_flag", type = "BOOL", mode = "NULLABLE" },
    { name = "velocity_1h", type = "INT64", mode = "NULLABLE" },
    { name = "status", type = "STRING", mode = "NULLABLE" },
    { name = "fraud_typology", type = "STRING", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "aml_compliance_alerts" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.fsi_fraud_demo.dataset_id
  table_id            = "aml_compliance_alerts"
  deletion_protection = false

  schema = jsonencode([
    { name = "alert_id", type = "STRING", mode = "REQUIRED" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "customer_id", type = "STRING", mode = "NULLABLE" },
    { name = "tx_id", type = "STRING", mode = "NULLABLE" },
    { name = "regulation_framework", type = "STRING", mode = "NULLABLE" },
    { name = "severity", type = "STRING", mode = "NULLABLE" },
    { name = "sar_filed", type = "BOOL", mode = "NULLABLE" },
    { name = "analyst_notes", type = "STRING", mode = "NULLABLE" },
    { name = "resolution_status", type = "STRING", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_job" "seed_fsi_demo_data" {
  project  = var.project_id
  job_id   = "seed_fsi_agentic_demo_${substr(md5("${var.project_id}-${var.bq_dataset_id}"), 0, 8)}"
  location = var.bq_location

  labels = {
    datacloud       = "jetski"
    goog-mcp-server = "true"
  }

  query {
    query = <<-EOT
      TRUNCATE TABLE `${var.project_id}.${var.bq_dataset_id}.customer_portfolios`;
      INSERT INTO `${var.project_id}.${var.bq_dataset_id}.customer_portfolios` VALUES
        ('CUST-1001', 'Vanguard Alpine Holdings S.p.A.', 'CORPORATE_TREASURY', 'ENHANCED_DUE_DILIGENCE', TRUE, 'CRITICAL', 14800000.00, 4200000.00, 'POTENTIAL_MATCH_OFAC', 'Marco Ferri', 'IT', DATE '2021-03-14'),
        ('CUST-1002', 'Elena Visconti', 'PRIVATE_BANKING', 'VERIFIED', FALSE, 'LOW', 3450000.00, 150000.00, 'CLEAR', 'Giulia Rossi', 'IT', DATE '2019-11-02'),
        ('CUST-1003', 'Meridian Cross-Border Trade Ltd', 'CORPORATE_TREASURY', 'ENHANCED_DUE_DILIGENCE', FALSE, 'HIGH', 8920000.00, 3100000.00, 'UNDER_INVESTIGATION', 'Marco Ferri', 'CH', DATE '2023-01-19'),
        ('CUST-1004', 'Alessandro Conti', 'AFFLUENT_RETAIL', 'VERIFIED', FALSE, 'MEDIUM', 620000.00, 85000.00, 'CLEAR', 'Luca Bianchi', 'IT', DATE '2022-06-25'),
        ('CUST-1005', 'Nordic Fintech Ventures GmbH', 'SME', 'EXPIRED_REVIEW', FALSE, 'HIGH', 1950000.00, 940000.00, 'CLEAR', 'Giulia Rossi', 'DE', DATE '2020-08-11'),
        ('CUST-1006', 'Baron Viktor Von Staufen', 'PRIVATE_BANKING', 'ENHANCED_DUE_DILIGENCE', TRUE, 'HIGH', 22100000.00, 5000000.00, 'CLEAR', 'Marco Ferri', 'AT', DATE '2018-04-30'),
        ('CUST-1007', 'Mediterranea Logistics S.r.l.', 'SME', 'VERIFIED', FALSE, 'LOW', 1120000.00, 310000.00, 'CLEAR', 'Luca Bianchi', 'IT', DATE '2021-09-15'),
        ('CUST-1008', 'Oasis Global Commodities FZE', 'CORPORATE_TREASURY', 'ENHANCED_DUE_DILIGENCE', TRUE, 'CRITICAL', 19400000.00, 7800000.00, 'UNDER_INVESTIGATION', 'Marco Ferri', 'AE', DATE '2024-02-01');

      TRUNCATE TABLE `${var.project_id}.${var.bq_dataset_id}.transactions_ledger`;
      INSERT INTO `${var.project_id}.${var.bq_dataset_id}.transactions_ledger` VALUES
        ('TX-90801', TIMESTAMP '2026-10-06 08:14:22 UTC', 'CUST-1001', 'IT60X0542811101000000123456', 'Cayman Horizon Escrow Ltd', 'OFFSHORE_TRUST_SERVICES', 'KY', 'SWIFT_WIRE', 485000.00, 96, TRUE, 5, 'FLAGGED', 'CROSS_BORDER_STRUCTURING'),
        ('TX-90802', TIMESTAMP '2026-10-06 08:19:05 UTC', 'CUST-1001', 'IT60X0542811101000000123456', 'Cayman Horizon Escrow Ltd', 'OFFSHORE_TRUST_SERVICES', 'KY', 'SWIFT_WIRE', 490000.00, 98, TRUE, 6, 'BLOCKED', 'CROSS_BORDER_STRUCTURING'),
        ('TX-90803', TIMESTAMP '2026-10-06 07:45:10 UTC', 'CUST-1003', 'CH9300762011623852957', 'Bosphorus Bullion Exchange', 'PRECIOUS_METALS', 'TR', 'SEPA_INSTANT', 240000.00, 89, TRUE, 4, 'FLAGGED', 'SYNTHETIC_IDENTITY'),
        ('TX-90804', TIMESTAMP '2026-10-06 07:12:40 UTC', 'CUST-1008', 'AE070331234567890123456', 'Gulf Crypto OTC Desk DMCC', 'CRYPTO_EXCHANGE', 'AE', 'SWIFT_WIRE', 1150000.00, 94, TRUE, 3, 'FLAGGED', 'CROSS_BORDER_STRUCTURING'),
        ('TX-90805', TIMESTAMP '2026-10-06 06:55:19 UTC', 'CUST-1005', 'DE89370400440532013000', 'Unknown Digital Voucher Hub', 'DIGITAL_GOODS', 'CY', 'API_GATEWAY', 78500.00, 87, TRUE, 14, 'BLOCKED', 'ACCOUNT_TAKEOVER'),
        ('TX-90806', TIMESTAMP '2026-10-06 06:30:00 UTC', 'CUST-1002', 'IT12A0306912345100000099887', 'Piazza Affari Asset Mgmt', 'WEALTH_MANAGEMENT', 'IT', 'SEPA_CREDIT', 125000.00, 12, FALSE, 1, 'SETTLED', 'NONE'),
        ('TX-90807', TIMESTAMP '2026-10-06 05:48:33 UTC', 'CUST-1006', 'AT611904300234573201', 'Geneva Fine Art Auctioneers', 'LUXURY_AUCTIONS', 'CH', 'SWIFT_WIRE', 680000.00, 76, TRUE, 2, 'PENDING_REVIEW', 'CROSS_BORDER_STRUCTURING'),
        ('TX-90808', TIMESTAMP '2026-10-06 05:10:12 UTC', 'CUST-1004', 'IT88K0200801600000010293847', 'Harrods London Luxury', 'LUXURY_RETAIL', 'GB', 'CARD_NOT_PRESENT', 19400.00, 68, TRUE, 8, 'FLAGGED', 'CARD_NOT_PRESENT_BURST'),
        ('TX-90809', TIMESTAMP '2026-10-06 04:22:09 UTC', 'CUST-1007', 'IT44P0103002800000004455667', 'Porto di Genova Terminal S.p.A.', 'MARITIME_LOGISTICS', 'IT', 'SEPA_CREDIT', 43200.00, 8, FALSE, 1, 'SETTLED', 'NONE'),
        ('TX-90810', TIMESTAMP '2026-10-05 22:15:44 UTC', 'CUST-1008', 'AE070331234567890123456', 'Singapore Straits Clearing Pte', 'COMMODITIES_BROKER', 'SG', 'SWIFT_WIRE', 890000.00, 91, TRUE, 4, 'FLAGGED', 'CROSS_BORDER_STRUCTURING'),
        ('TX-90811', TIMESTAMP '2026-10-05 19:04:11 UTC', 'CUST-1003', 'CH9300762011623852957', 'Baltic NeoPay Clearing', 'PAYMENT_FACILITATOR', 'LT', 'SEPA_INSTANT', 165000.00, 82, TRUE, 7, 'FLAGGED', 'ACCOUNT_TAKEOVER'),
        ('TX-90812', TIMESTAMP '2026-10-05 16:40:00 UTC', 'CUST-1002', 'IT12A0306912345100000099887', 'Borsa Italiana Bond Desk', 'SECURITIES', 'IT', 'SEPA_CREDIT', 310000.00, 9, FALSE, 1, 'SETTLED', 'NONE');

      TRUNCATE TABLE `${var.project_id}.${var.bq_dataset_id}.aml_compliance_alerts`;
      INSERT INTO `${var.project_id}.${var.bq_dataset_id}.aml_compliance_alerts` VALUES
        ('AML-5001', TIMESTAMP '2026-10-06 08:20:00 UTC', 'CUST-1001', 'TX-90802', 'EU_AMLD6', 'CRITICAL', TRUE, 'Split wire transfers just under 500k EUR reporting threshold to Cayman escrow within 5 minutes. PEP + OFAC potential match.', 'ESCALATED_FIU'),
        ('AML-5002', TIMESTAMP '2026-10-06 07:46:00 UTC', 'CUST-1003', 'TX-90803', 'FATF_WIRE_RULE', 'HIGH', FALSE, 'Rapid SEPA Instant bullion purchase in high-risk corridor with incomplete beneficiary UBO metadata.', 'OPEN_INVESTIGATION'),
        ('AML-5003', TIMESTAMP '2026-10-06 07:15:00 UTC', 'CUST-1008', 'TX-90804', 'EU_AMLD6', 'CRITICAL', TRUE, '1.15M EUR wire to unhosted crypto OTC liquidity desk in Dubai; PEP corporate director flagged.', 'ESCALATED_FIU'),
        ('AML-5004', TIMESTAMP '2026-10-06 06:56:00 UTC', 'CUST-1005', 'TX-90805', 'PSD3_FRAUD', 'HIGH', FALSE, 'API credential stuffing burst (14 calls/hr) attempting digital voucher liquidation; KYC review expired.', 'BLOCKED_AUTO'),
        ('AML-5005', TIMESTAMP '2026-10-06 05:50:00 UTC', 'CUST-1006', 'TX-90807', 'EU_AMLD6', 'MEDIUM', FALSE, 'High-value fine art auction transfer by PEP client; awaiting invoice provenance verification.', 'PENDING_EDD'),
        ('AML-5006', TIMESTAMP '2026-10-06 05:12:00 UTC', 'CUST-1004', 'TX-90808', 'PSD3_FRAUD', 'MEDIUM', FALSE, 'Unusual velocity of Card-Not-Present luxury transactions in UK outside normal Italian geo-profile.', 'CUSTOMER_CHALLENGED');
    EOT

    create_disposition = ""
    write_disposition  = ""
  }

  depends_on = [
    google_bigquery_table.customer_portfolios,
    google_bigquery_table.transactions_ledger,
    google_bigquery_table.aml_compliance_alerts,
  ]
}
