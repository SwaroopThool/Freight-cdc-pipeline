from fastapi import APIRouter, HTTPException
from database import pg
from schemas import JobIn

router = APIRouter()

@router.get("/")
def list_jobs():
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM job")
        return cur.fetchall()

@router.get("/{id}")
def get_job(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM job WHERE id = %s", (id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.post("/", status_code=201)
def create_job(body: JobIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO job (shipment_id, type, status, assigned_to, due_at) VALUES (%s,%s,%s,%s,%s) RETURNING *",
            (body.shipment_id, body.type, body.status, body.assigned_to, body.due_at),
        )
        return cur.fetchone()

@router.put("/{id}")
def update_job(id: int, body: JobIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE job SET shipment_id=%s, type=%s, status=%s, assigned_to=%s, due_at=%s WHERE id=%s RETURNING *",
            (body.shipment_id, body.type, body.status, body.assigned_to, body.due_at, id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.delete("/{id}", status_code=204)
def delete_job(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM job WHERE id=%s", (id,))
