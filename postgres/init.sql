-- ============================================================
-- Freight CDC — PostgreSQL Schema
-- ============================================================

-- ── Locations (airports, seaports, road hubs) ───────────────
CREATE TABLE location (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    city        VARCHAR(100) NOT NULL,
    country     VARCHAR(100) NOT NULL,
    type        VARCHAR(10)  NOT NULL CHECK (type IN ('air', 'water', 'road')),
    lat         NUMERIC(10,6),
    lon         NUMERIC(10,6),
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- ── Vehicles (trucks, ships, planes) ────────────────────────
CREATE TABLE vehicle (
    id                   SERIAL PRIMARY KEY,
    name                 VARCHAR(200) NOT NULL,
    type                 VARCHAR(10)  NOT NULL CHECK (type IN ('truck', 'ship', 'plane')),
    capacity_kg          NUMERIC(12,2) NOT NULL,
    current_location_id  INTEGER REFERENCES location(id),
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- ── Freight (cargo items) ────────────────────────────────────
CREATE TABLE freight (
    id          SERIAL PRIMARY KEY,
    description TEXT         NOT NULL,
    weight_kg   NUMERIC(12,2) NOT NULL,
    type        VARCHAR(50)  NOT NULL,
    value_usd   NUMERIC(15,2) NOT NULL,
    status      VARCHAR(20)  NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','in_transit','delivered','damaged')),
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- ── Purchase Orders ──────────────────────────────────────────
CREATE TABLE purchase_order (
    id              SERIAL PRIMARY KEY,
    customer_name   VARCHAR(200) NOT NULL,
    origin_id       INTEGER      NOT NULL REFERENCES location(id),
    destination_id  INTEGER      NOT NULL REFERENCES location(id),
    status          VARCHAR(20)  NOT NULL DEFAULT 'new'
                    CHECK (status IN ('new','confirmed','in_progress','completed','cancelled')),
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

-- ── Shipments ────────────────────────────────────────────────
CREATE TABLE shipment (
    id              SERIAL PRIMARY KEY,
    po_id           INTEGER      NOT NULL REFERENCES purchase_order(id),
    vehicle_id      INTEGER      NOT NULL REFERENCES vehicle(id),
    mode            VARCHAR(10)  NOT NULL CHECK (mode IN ('air','water','road')),
    origin_id       INTEGER      NOT NULL REFERENCES location(id),
    destination_id  INTEGER      NOT NULL REFERENCES location(id),
    status          VARCHAR(20)  NOT NULL DEFAULT 'scheduled'
                    CHECK (status IN ('scheduled','in_transit','arrived','cancelled')),
    scheduled_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

-- ── Jobs (tasks within a shipment) ──────────────────────────
CREATE TABLE job (
    id           SERIAL PRIMARY KEY,
    shipment_id  INTEGER      NOT NULL REFERENCES shipment(id),
    type         VARCHAR(20)  NOT NULL CHECK (type IN ('pickup','customs','delivery')),
    status       VARCHAR(20)  NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending','in_progress','completed','failed')),
    assigned_to  VARCHAR(200),
    due_at       TIMESTAMPTZ,
    created_at   TIMESTAMPTZ  DEFAULT NOW()
);

-- ── Invoices ─────────────────────────────────────────────────
CREATE TABLE invoice (
    id          SERIAL PRIMARY KEY,
    po_id       INTEGER       NOT NULL REFERENCES purchase_order(id),
    amount_usd  NUMERIC(15,2) NOT NULL,
    status      VARCHAR(10)   NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft','sent','paid')),
    due_date    DATE          NOT NULL,
    created_at  TIMESTAMPTZ   DEFAULT NOW()
);

-- ── Tracking Events (GPS positions for vehicles) ─────────────
CREATE TABLE tracking_event (
    id           SERIAL PRIMARY KEY,
    vehicle_id   INTEGER       NOT NULL REFERENCES vehicle(id),
    shipment_id  INTEGER       REFERENCES shipment(id),
    lat          NUMERIC(10,6) NOT NULL,
    lon          NUMERIC(10,6) NOT NULL,
    speed_kmh    NUMERIC(6,2)  DEFAULT 0,
    timestamp    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    hop_number   INTEGER       NOT NULL DEFAULT 0
);

-- ── Indexes ──────────────────────────────────────────────────
CREATE INDEX idx_shipment_po       ON shipment(po_id);
CREATE INDEX idx_shipment_vehicle  ON shipment(vehicle_id);
CREATE INDEX idx_job_shipment      ON job(shipment_id);
CREATE INDEX idx_invoice_po        ON invoice(po_id);
CREATE INDEX idx_tracking_vehicle  ON tracking_event(vehicle_id);
CREATE INDEX idx_tracking_shipment ON tracking_event(shipment_id);
CREATE INDEX idx_tracking_ts       ON tracking_event(timestamp DESC);

-- ── Logical replication publication (for Debezium) ───────────
CREATE PUBLICATION freight_pub FOR TABLE
    location, vehicle, freight, purchase_order,
    shipment, job, invoice, tracking_event;

-- ── Seed: Locations ──────────────────────────────────────────
INSERT INTO location (name, city, country, type, lat, lon) VALUES
    ('JFK International Airport',   'New York',     'USA',         'air',   40.6413,  -73.7781),
    ('LAX International Airport',   'Los Angeles',  'USA',         'air',   33.9425, -118.4081),
    ('Heathrow Airport',             'London',       'UK',          'air',   51.4700,   -0.4543),
    ('Changi Airport',               'Singapore',    'Singapore',   'air',    1.3644,  103.9915),
    ('Dubai International Airport', 'Dubai',        'UAE',         'air',   25.2532,   55.3657),
    ('Port of Los Angeles',         'Los Angeles',  'USA',         'water', 33.7395, -118.2659),
    ('Port of Rotterdam',            'Rotterdam',    'Netherlands', 'water', 51.9225,    4.4792),
    ('Port of Shanghai',             'Shanghai',     'China',       'water', 30.6272,  121.9749),
    ('Chicago Road Hub',             'Chicago',      'USA',         'road',  41.8781,  -87.6298),
    ('Frankfurt Road Hub',           'Frankfurt',    'Germany',     'road',  50.1109,    8.6821);

-- ── Seed: Vehicles ───────────────────────────────────────────
INSERT INTO vehicle (name, type, capacity_kg, current_location_id) VALUES
    ('Boeing 747F Alpha',    'plane', 102000,     1),
    ('Boeing 747F Beta',     'plane', 102000,     3),
    ('Airbus A330F',         'plane',  70000,     4),
    ('MSC Zoe',              'ship',  197000000,  6),
    ('Maersk Alabama',       'ship',  150000000,  7),
    ('COSCO Nebula',         'ship',  180000000,  8),
    ('Volvo FH16 T1',        'truck',  25000,     9),
    ('Volvo FH16 T2',        'truck',  25000,     9),
    ('Mercedes Actros T1',   'truck',  20000,    10),
    ('DAF XF T1',            'truck',  22000,    10);
