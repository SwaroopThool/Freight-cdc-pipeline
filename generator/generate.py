"""
Continuous data generator — inserts freight logistics events into PostgreSQL.
Every 500ms: 1-3 tracking events.
Every 5s:    new purchase_order → shipment → 3 jobs → invoice.
Every 10s:   advance random shipment / job / invoice statuses.
"""

import os, random, time, logging
from datetime import date, timedelta
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [generator] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

DSN      = os.environ["POSTGRES_DSN"]
INTERVAL = int(os.environ.get("INSERT_INTERVAL_MS", "500")) / 1000.0

SHIPMENT_STATUS = ["scheduled", "in_transit", "arrived"]
JOB_STATUS      = ["pending", "in_progress", "completed"]
PO_STATUS       = ["new", "confirmed", "in_progress", "completed"]
INVOICE_STATUS  = ["draft", "sent", "paid"]
FREIGHT_STATUS  = ["pending", "in_transit", "delivered"]
FREIGHT_TYPES   = ["electronics", "perishable", "hazmat", "general", "automotive"]
CUSTOMERS       = ["Acme Logistics", "Global Freight Co", "SwiftShip", "OceanBridge", "AirCargo Inc",
                   "Road Masters", "PrimeFreight", "FastLane Ltd", "TradeRoute AG", "PeakShipping"]
STAFF           = ["Alice Chen", "Bob Patel", "Carlos Diaz", "Diana Osei", "Erik Müller",
                   "Fatima Al-Rashid", "George Kim", "Hannah Schmidt", "Ivan Torres", "Julia Novak"]
MODE_VEHICLE    = {"air": "plane", "water": "ship", "road": "truck"}

# Realistic speed ranges (km/h) and lat/lon movement per hop per vehicle type
VEHICLE_PROFILE = {
    "truck": {"speed": (30,  120),  "dlat": 0.05, "dlon": 0.08},
    "ship":  {"speed": (10,   45),  "dlat": 0.40, "dlon": 0.60},
    "plane": {"speed": (600, 950),  "dlat": 1.50, "dlon": 2.00},
}


def connect(retries=20):
    for i in range(retries):
        try:
            conn = psycopg2.connect(DSN)
            log.info("Connected to PostgreSQL.")
            return conn
        except psycopg2.OperationalError:
            log.info("DB not ready, retry %d/%d…", i + 1, retries)
            time.sleep(3)
    raise RuntimeError("Cannot connect to PostgreSQL")


def ids(cur, table):
    cur.execute(f"SELECT id FROM {table}")
    return [r[0] for r in cur.fetchall()]


def vehicle_list(cur):
    cur.execute("SELECT id, type FROM vehicle")
    return cur.fetchall()


def insert_tracking(cur, vehicles, shipment_ids):
    for _ in range(random.randint(1, 3)):
        vid, vtype = random.choice(vehicles)
        sid = random.choice(shipment_ids) if shipment_ids else None

        profile = VEHICLE_PROFILE.get(vtype, VEHICLE_PROFILE["truck"])
        speed_min, speed_max = profile["speed"]

        cur.execute(
            "SELECT MAX(hop_number), "
            "       (SELECT lat FROM tracking_event WHERE vehicle_id = %s ORDER BY hop_number DESC LIMIT 1), "
            "       (SELECT lon FROM tracking_event WHERE vehicle_id = %s ORDER BY hop_number DESC LIMIT 1) "
            "FROM tracking_event WHERE vehicle_id = %s",
            (vid, vid, vid),
        )
        row = cur.fetchone()
        hop = (row[0] or 0) + 1
        base_lat = float(row[1]) if row[1] else random.uniform(-60, 60)
        base_lon = float(row[2]) if row[2] else random.uniform(-170, 170)

        lat   = round(base_lat + random.uniform(-profile["dlat"], profile["dlat"]), 6)
        lon   = round(base_lon + random.uniform(-profile["dlon"], profile["dlon"]), 6)
        speed = round(random.uniform(speed_min, speed_max), 1)

        cur.execute(
            "INSERT INTO tracking_event (vehicle_id, shipment_id, lat, lon, speed_kmh, hop_number)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            (vid, sid, lat, lon, speed, hop),
        )


def create_order_chain(cur, location_ids, vehicle_ids):
    origin_id, dest_id = random.sample(location_ids, 2)
    cur.execute("SELECT type FROM location WHERE id = %s", (origin_id,))
    mode = cur.fetchone()[0]

    cur.execute(
        "INSERT INTO purchase_order (customer_name, origin_id, destination_id) VALUES (%s,%s,%s) RETURNING id",
        (random.choice(CUSTOMERS), origin_id, dest_id),
    )
    po_id = cur.fetchone()[0]

    cur.execute(
        "SELECT id FROM vehicle WHERE type = %s ORDER BY RANDOM() LIMIT 1",
        (MODE_VEHICLE[mode],),
    )
    row = cur.fetchone()
    vid = row[0] if row else random.choice(vehicle_ids)

    cur.execute(
        "INSERT INTO shipment (po_id, vehicle_id, mode, origin_id, destination_id) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (po_id, vid, mode, origin_id, dest_id),
    )
    ship_id = cur.fetchone()[0]

    for jtype in ("pickup", "customs", "delivery"):
        cur.execute(
            "INSERT INTO job (shipment_id, type, assigned_to, due_at) VALUES (%s,%s,%s, NOW() + INTERVAL '3 days')",
            (ship_id, jtype, random.choice(STAFF)),
        )

    cur.execute(
        "INSERT INTO freight (description, weight_kg, type, value_usd) VALUES (%s,%s,%s,%s)",
        (f"Cargo for PO#{po_id}", round(random.uniform(50, 20000), 1),
         random.choice(FREIGHT_TYPES), round(random.uniform(500, 200000), 2)),
    )
    cur.execute(
        "INSERT INTO invoice (po_id, amount_usd, due_date) VALUES (%s,%s,%s)",
        (po_id, round(random.uniform(1000, 150000), 2), date.today() + timedelta(days=30)),
    )
    log.info("New chain: PO=%d shipment=%d mode=%s", po_id, ship_id, mode)


def advance_statuses(cur):
    for table, col, progression in [
        ("shipment", "status", SHIPMENT_STATUS),
        ("job",      "status", JOB_STATUS),
        ("purchase_order", "status", PO_STATUS),
        ("invoice",  "status", INVOICE_STATUS),
    ]:
        for i, current in enumerate(progression[:-1]):
            nxt = progression[i + 1]
            cur.execute(
                f"UPDATE {table} SET {col} = %s WHERE id IN "
                f"(SELECT id FROM {table} WHERE {col} = %s ORDER BY RANDOM() LIMIT 2)",
                (nxt, current),
            )


def main():
    conn = connect()
    tick = 0
    while True:
        try:
            with conn:
                with conn.cursor() as cur:
                    loc_ids  = ids(cur, "location")
                    vehs     = vehicle_list(cur)
                    veh_ids  = [v[0] for v in vehs]
                    ship_ids = ids(cur, "shipment")

                    insert_tracking(cur, vehs, ship_ids)

                    if tick % 10 == 0:
                        create_order_chain(cur, loc_ids, veh_ids)

                    if tick % 20 == 0:
                        advance_statuses(cur)

            tick += 1
            time.sleep(INTERVAL)

        except psycopg2.OperationalError as e:
            log.error("DB lost: %s — reconnecting…", e)
            time.sleep(5)
            conn = connect()
        except KeyboardInterrupt:
            break

    conn.close()


if __name__ == "__main__":
    main()
