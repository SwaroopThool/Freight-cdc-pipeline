-- ============================================================
-- Materialize Setup — Kafka Sources, Views, Sinks
-- Uses FORMAT JSON (no envelope)
-- Each Debezium CDC event becomes one row in the source.
-- ============================================================

-- ── Kafka connection to Redpanda ─────────────────────────────
CREATE CONNECTION IF NOT EXISTS redpanda_conn
  TO KAFKA (
    BROKER 'redpanda:9092',
    SECURITY PROTOCOL = 'PLAINTEXT'
  );

-- ── Cluster ───────────────────────────────────────────────────
DROP CLUSTER IF EXISTS ingest_cluster CASCADE;
CREATE CLUSTER ingest_cluster (SIZE = '25cc', REPLICATION FACTOR = 1);

-- ── Sources (FORMAT JSON, no envelope) ───────────────────────
CREATE SOURCE src_location
  IN CLUSTER ingest_cluster
  FROM KAFKA CONNECTION redpanda_conn (TOPIC 'freight_db.public.location')
  FORMAT JSON;

CREATE SOURCE src_vehicle
  IN CLUSTER ingest_cluster
  FROM KAFKA CONNECTION redpanda_conn (TOPIC 'freight_db.public.vehicle')
  FORMAT JSON;

CREATE SOURCE src_freight
  IN CLUSTER ingest_cluster
  FROM KAFKA CONNECTION redpanda_conn (TOPIC 'freight_db.public.freight')
  FORMAT JSON;

CREATE SOURCE src_purchase_order
  IN CLUSTER ingest_cluster
  FROM KAFKA CONNECTION redpanda_conn (TOPIC 'freight_db.public.purchase_order')
  FORMAT JSON;

CREATE SOURCE src_shipment
  IN CLUSTER ingest_cluster
  FROM KAFKA CONNECTION redpanda_conn (TOPIC 'freight_db.public.shipment')
  FORMAT JSON;

CREATE SOURCE src_job
  IN CLUSTER ingest_cluster
  FROM KAFKA CONNECTION redpanda_conn (TOPIC 'freight_db.public.job')
  FORMAT JSON;

CREATE SOURCE src_invoice
  IN CLUSTER ingest_cluster
  FROM KAFKA CONNECTION redpanda_conn (TOPIC 'freight_db.public.invoice')
  FORMAT JSON;

CREATE SOURCE src_tracking_event
  IN CLUSTER ingest_cluster
  FROM KAFKA CONNECTION redpanda_conn (TOPIC 'freight_db.public.tracking_event')
  FORMAT JSON;

-- ── Materialized Views ────────────────────────────────────────
-- With FORMAT JSON and no envelope, each source row has a single
-- 'data' column containing the raw JSON. Extract fields with ->>.

CREATE MATERIALIZED VIEW v_shipments
  IN CLUSTER ingest_cluster AS
  SELECT
    (data->'payload'->'after'->>'id')::int          AS id,
    (data->'payload'->'after'->>'mode')::text        AS mode,
    (data->'payload'->'after'->>'status')::text      AS status,
    (data->'payload'->'after'->>'origin_id')::int    AS origin_id,
    (data->'payload'->'after'->>'destination_id')::int AS destination_id
  FROM src_shipment
  WHERE data->'payload'->>'op' != 'd'
    AND data->'payload'->'after' IS NOT NULL;

CREATE MATERIALIZED VIEW v_jobs
  IN CLUSTER ingest_cluster AS
  SELECT
    (data->'payload'->'after'->>'id')::int          AS id,
    (data->'payload'->'after'->>'shipment_id')::int  AS shipment_id,
    (data->'payload'->'after'->>'type')::text        AS type,
    (data->'payload'->'after'->>'status')::text      AS status,
    (data->'payload'->'after'->>'assigned_to')::text AS assigned_to
  FROM src_job
  WHERE data->'payload'->>'op' != 'd'
    AND data->'payload'->'after' IS NOT NULL;

CREATE MATERIALIZED VIEW v_invoices
  IN CLUSTER ingest_cluster AS
  SELECT
    (data->'payload'->'after'->>'id')::int           AS id,
    (data->'payload'->'after'->>'po_id')::int        AS po_id,
    (data->'payload'->'after'->>'amount_usd')::float AS amount_usd,
    (data->'payload'->'after'->>'status')::text      AS status
  FROM src_invoice
  WHERE data->'payload'->>'op' != 'd'
    AND data->'payload'->'after' IS NOT NULL;

-- Aggregate views for the dashboard
CREATE MATERIALIZED VIEW v_active_shipments
  IN CLUSTER ingest_cluster AS
  SELECT mode, status, COUNT(*) AS shipment_count
  FROM v_shipments
  GROUP BY mode, status;

CREATE MATERIALIZED VIEW v_revenue_by_route
  IN CLUSTER ingest_cluster AS
  SELECT
    s.origin_id,
    s.destination_id,
    COUNT(*)          AS order_count,
    SUM(i.amount_usd) AS total_revenue_usd
  FROM v_invoices i
  JOIN (
    SELECT DISTINCT
      (data->'payload'->'after'->>'id')::int   AS id,
      (data->'payload'->'after'->>'origin_id')::int AS origin_id,
      (data->'payload'->'after'->>'destination_id')::int AS destination_id
    FROM src_purchase_order
    WHERE data->'payload'->>'op' != 'd'
      AND data->'payload'->'after' IS NOT NULL
  ) s ON s.id = i.po_id
  GROUP BY s.origin_id, s.destination_id;

CREATE MATERIALIZED VIEW v_job_summary
  IN CLUSTER ingest_cluster AS
  SELECT status, COUNT(*) AS job_count
  FROM v_jobs
  GROUP BY status;

CREATE MATERIALIZED VIEW v_invoice_aging
  IN CLUSTER ingest_cluster AS
  SELECT status, COUNT(*) AS invoice_count, SUM(amount_usd) AS total_amount_usd
  FROM v_invoices
  GROUP BY status;

-- ── Sinks → publish aggregate views back to Redpanda ─────────
CREATE SINK sink_active_shipments
  IN CLUSTER ingest_cluster FROM v_active_shipments
  INTO KAFKA CONNECTION redpanda_conn (TOPIC 'mz.active_shipments')
  KEY (mode, status) FORMAT JSON ENVELOPE UPSERT;

CREATE SINK sink_revenue_by_route
  IN CLUSTER ingest_cluster FROM v_revenue_by_route
  INTO KAFKA CONNECTION redpanda_conn (TOPIC 'mz.revenue_by_route')
  KEY (origin_id, destination_id) FORMAT JSON ENVELOPE UPSERT;

CREATE SINK sink_job_summary
  IN CLUSTER ingest_cluster FROM v_job_summary
  INTO KAFKA CONNECTION redpanda_conn (TOPIC 'mz.job_summary')
  KEY (status) FORMAT JSON ENVELOPE UPSERT;
