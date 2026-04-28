from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import locations, vehicles, freights, purchase_orders, shipments, jobs, invoices, tracking_events

app = FastAPI(title="Freight CDC API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(locations.router,       prefix="/locations",        tags=["Locations"])
app.include_router(vehicles.router,        prefix="/vehicles",         tags=["Vehicles"])
app.include_router(freights.router,        prefix="/freights",         tags=["Freight"])
app.include_router(purchase_orders.router, prefix="/purchase-orders",  tags=["Purchase Orders"])
app.include_router(shipments.router,       prefix="/shipments",        tags=["Shipments"])
app.include_router(jobs.router,            prefix="/jobs",             tags=["Jobs"])
app.include_router(invoices.router,        prefix="/invoices",         tags=["Invoices"])
app.include_router(tracking_events.router, prefix="/tracking",         tags=["Tracking"])

@app.get("/health")
def health():
    return {"status": "ok"}
