from fastapi import APIRouter, HTTPException
from database import pg
from schemas import VehicleIn

router = APIRouter()

@router.get("/")
def list_vehicles():
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM vehicle")
        return cur.fetchall()

@router.get("/{id}")
def get_vehicle(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM vehicle WHERE id = %s", (id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.post("/", status_code=201)
def create_vehicle(body: VehicleIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO vehicle (name, type, capacity_kg, current_location_id) VALUES (%s,%s,%s,%s) RETURNING *",
            (body.name, body.type, body.capacity_kg, body.current_location_id),
        )
        return cur.fetchone()

@router.put("/{id}")
def update_vehicle(id: int, body: VehicleIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE vehicle SET name=%s, type=%s, capacity_kg=%s, current_location_id=%s WHERE id=%s RETURNING *",
            (body.name, body.type, body.capacity_kg, body.current_location_id, id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.delete("/{id}", status_code=204)
def delete_vehicle(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM vehicle WHERE id=%s", (id,))
