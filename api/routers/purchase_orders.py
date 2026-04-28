from fastapi import APIRouter, HTTPException
from database import pg
from schemas import PurchaseOrderIn

router = APIRouter()

@router.get("/")
def list_purchase_orders():
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM purchase_order")
        return cur.fetchall()

@router.get("/{id}")
def get_purchase_order(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM purchase_order WHERE id = %s", (id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.post("/", status_code=201)
def create_purchase_order(body: PurchaseOrderIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO purchase_order (customer_name, origin_id, destination_id, status) VALUES (%s,%s,%s,%s) RETURNING *",
            (body.customer_name, body.origin_id, body.destination_id, body.status),
        )
        return cur.fetchone()

@router.put("/{id}")
def update_purchase_order(id: int, body: PurchaseOrderIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE purchase_order SET customer_name=%s, origin_id=%s, destination_id=%s, status=%s WHERE id=%s RETURNING *",
            (body.customer_name, body.origin_id, body.destination_id, body.status, id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.delete("/{id}", status_code=204)
def delete_purchase_order(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM purchase_order WHERE id=%s", (id,))
