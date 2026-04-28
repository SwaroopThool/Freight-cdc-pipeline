from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class LocationIn(BaseModel):
    name: str; city: str; country: str; type: str
    lat: Optional[float] = None; lon: Optional[float] = None

class VehicleIn(BaseModel):
    name: str; type: str; capacity_kg: float
    current_location_id: Optional[int] = None

class FreightIn(BaseModel):
    description: str; weight_kg: float; type: str; value_usd: float
    status: str = "pending"

class PurchaseOrderIn(BaseModel):
    customer_name: str; origin_id: int; destination_id: int
    status: str = "new"

class ShipmentIn(BaseModel):
    po_id: int; vehicle_id: int; mode: str
    origin_id: int; destination_id: int; status: str = "scheduled"

class JobIn(BaseModel):
    shipment_id: int; type: str; status: str = "pending"
    assigned_to: Optional[str] = None; due_at: Optional[datetime] = None

class InvoiceIn(BaseModel):
    po_id: int; amount_usd: float; status: str = "draft"; due_date: date

class TrackingEventIn(BaseModel):
    vehicle_id: int; shipment_id: Optional[int] = None
    lat: float; lon: float; speed_kmh: float = 0.0; hop_number: int = 0
