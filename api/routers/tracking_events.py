from fastapi import APIRouter, HTTPException
from database import pg
from schemas import TrackingEventIn

router = APIRouter()

@router.get("/")
def list_tracking(limit: int = 100):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM tracking_event ORDER BY timestamp DESC LIMIT %s", (limit,))
        return cur.fetchall()

@router.get("/vehicle/{vehicle_id}")
def get_vehicle_track(vehicle_id: int, limit: int = 50):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM tracking_event WHERE vehicle_id = %s ORDER BY timestamp DESC LIMIT %s",
            (vehicle_id, limit),
        )
        return cur.fetchall()

@router.post("/", status_code=201)
def create_tracking_event(body: TrackingEventIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO tracking_event (vehicle_id, shipment_id, lat, lon, speed_kmh, hop_number) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *",
            (body.vehicle_id, body.shipment_id, body.lat, body.lon, body.speed_kmh, body.hop_number),
        )
        return cur.fetchone()
