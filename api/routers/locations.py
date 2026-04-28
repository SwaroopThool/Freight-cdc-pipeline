from fastapi import APIRouter, HTTPException
from database import pg
from schemas import LocationIn

router = APIRouter()

@router.get("/")
def list_locations():
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM location")
        return cur.fetchall()

@router.get("/{id}")
def get_location(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM location WHERE id = %s", (id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.post("/", status_code=201)
def create_location(body: LocationIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO location (name, city, country, type, lat, lon) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *",
            (body.name, body.city, body.country, body.type, body.lat, body.lon),
        )
        return cur.fetchone()

@router.put("/{id}")
def update_location(id: int, body: LocationIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE location SET name=%s, city=%s, country=%s, type=%s, lat=%s, lon=%s WHERE id=%s RETURNING *",
            (body.name, body.city, body.country, body.type, body.lat, body.lon, id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.delete("/{id}", status_code=204)
def delete_location(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM location WHERE id=%s", (id,))
