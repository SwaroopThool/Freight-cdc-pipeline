from fastapi import APIRouter, HTTPException
from database import pg
from schemas import InvoiceIn

router = APIRouter()

@router.get("/")
def list_invoices():
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM invoice")
        return cur.fetchall()

@router.get("/{id}")
def get_invoice(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM invoice WHERE id = %s", (id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.post("/", status_code=201)
def create_invoice(body: InvoiceIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO invoice (po_id, amount_usd, status, due_date) VALUES (%s,%s,%s,%s) RETURNING *",
            (body.po_id, body.amount_usd, body.status, body.due_date),
        )
        return cur.fetchone()

@router.put("/{id}")
def update_invoice(id: int, body: InvoiceIn):
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE invoice SET po_id=%s, amount_usd=%s, status=%s, due_date=%s WHERE id=%s RETURNING *",
            (body.po_id, body.amount_usd, body.status, body.due_date, id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

@router.delete("/{id}", status_code=204)
def delete_invoice(id: int):
    with pg() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM invoice WHERE id=%s", (id,))
