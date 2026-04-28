from fastapi import APIRouter, HTTPException
from database import pg
from schemas import ShipmentIn

router = APIRouter()

@router.get("/")
def list_shipments():
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM shipment")
        return cur.fetchall()

@router.get("/{id}")
def get_shipment(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM shipment WHERE id = %s", (id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.post("/", status_code=201)
def create_shipment(body: ShipmentIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO shipment (po_id, vehicle_id, mode, origin_id, destination_id, status) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *",
            (body.po_id, body.vehicle_id, body.mode, body.origin_id, body.destination_id, body.status),
        )
        return cur.fetchone()

@router.put("/{id}")
def update_shipment(id: int, body: ShipmentIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE shipment SET po_id=%s, vehicle_id=%s, mode=%s, origin_id=%s, destination_id=%s, status=%s WHERE id=%s RETURNING *",
            (body.po_id, body.vehicle_id, body.mode, body.origin_id, body.destination_id, body.status, id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.delete("/{id}", status_code=204)
def delete_shipment(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM shipment WHERE id=%s", (id,))
