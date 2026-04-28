from fastapi import APIRouter, HTTPException
from database import pg
from schemas import FreightIn

router = APIRouter()

@router.get("/")
def list_freights():
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM freight")
        return cur.fetchall()

@router.get("/{id}")
def get_freight(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM freight WHERE id = %s", (id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.post("/", status_code=201)
def create_freight(body: FreightIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO freight (description, weight_kg, type, value_usd, status) VALUES (%s,%s,%s,%s,%s) RETURNING *",
            (body.description, body.weight_kg, body.type, body.value_usd, body.status),
        )
        return cur.fetchone()

@router.put("/{id}")
def update_freight(id: int, body: FreightIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE freight SET description=%s, weight_kg=%s, type=%s, value_usd=%s, status=%s WHERE id=%s RETURNING *",
            (body.description, body.weight_kg, body.type, body.value_usd, body.status, id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.delete("/{id}", status_code=204)
def delete_freight(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM freight WHERE id=%s", (id,))
