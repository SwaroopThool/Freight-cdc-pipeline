# Freight CDC — Real-Time Logistics Data Pipeline

A full Change Data Capture (CDC) pipeline for a logistics company handling freight via **air**, **water**, and **road**. Every database write flows automatically through Debezium → Redpanda → Materialize → live dashboard and REST API.

---

## Architecture

```
┌─────────────────┐
│  Data Generator │  inserts freight events every 500ms
└────────┬────────┘
         │ INSERT
         ▼
┌─────────────────┐    WAL / pgoutput
│   PostgreSQL    │──────────────────────► Debezium Kafka Connect
│  (source DB)    │                                │
└─────────────────┘                    JSON CDC events
                                                   │
                                                   ▼
                                          ┌─────────────────┐
                                          │    Redpanda     │  Kafka-compatible broker
                                          │  (8 CDC topics) │  freight_db.public.*
                                          └────────┬────────┘
                                                   │
                                                   ▼
                                          ┌─────────────────┐
                                          │  Materialize    │  streaming SQL engine
                                          │  (views+sinks)  │
                                          └────────┬────────┘
                                    ┌──────────────┼──────────────┐
                                    ▼              ▼              ▼
                             Redpanda sink    FastAPI       Streamlit
                             topics (mz.*)   CRUD API      Dashboard
                                    │
                                    ▼
                             Kafka Consumer
```

---

## Stack

| Component | Technology |
|---|---|
| Source database | PostgreSQL 16 (logical replication) |
| CDC tool | Debezium 2.7 (Kafka Connect) |
| Message broker | Redpanda v24.3.6 (Kafka-compatible) |
| Streaming SQL | Materialize (materialized views + sinks) |
| REST API | FastAPI + psycopg2 |
| Dashboard | Streamlit + Plotly |
| Orchestration | Docker Compose |
| Cloud IaC | Terraform (AWS EC2) (TODO)|

---

## Domain Entities

| Entity | Description |
|---|---|
| `location` | Airports, seaports, road hubs |
| `vehicle` | Trucks, ships, planes |
| `freight` | Cargo items with weight, type, value |
| `purchase_order` | Customer orders with origin/destination |
| `shipment` | Links a PO to a vehicle and transport mode |
| `job` | Tasks within a shipment (pickup, customs, delivery) |
| `invoice` | Billing document linked to a purchase order |
| `tracking_event` | GPS position of a vehicle at a given hop |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — set memory to **at least 6 GB** in Settings → Resources
- Ports free: `5432`, `6875`, `8000`, `8080`, `8083`, `8501`, `19092`

---

## Running Locally

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/freight-cdc.git
cd freight-cdc

# 2. Start all services (~5 min on first run — pulls images + builds)
docker compose up --build
```

Steps 3 and 4 are **fully automated** by two one-shot Docker Compose services:

- `debezium-setup` — waits for Debezium to be healthy, then runs `register-connector.sh` to register the Postgres connector.
- `materialize-setup` — waits for Materialize and Debezium to be healthy, then runs `setup.sql` to create sources, views, and sinks.

If the pipeline isn't flowing, check whether either one-shot container exited with an error:

```bash
docker ps -a --filter name=debezium-setup --filter name=materialize-setup
```

If either shows a non-zero exit code, rerun it:

```bash
# Rerun Debezium connector registration
docker compose run --rm debezium-setup

# Rerun Materialize setup
docker compose run --rm materialize-setup
```

---

## Verifying the Pipeline

| What to check | Where |
|---|---|
| CDC topics flowing | Redpanda Console → `http://localhost:8080` |
| Live dashboard | Streamlit → `http://localhost:8501` |
| REST API (Swagger) | FastAPI → `http://localhost:8000/docs` |
| Materialize views | `psql -h localhost -p 6875 -U materialize` |
| Consumer events | `docker logs -f consumer` |

**Confirm CDC is working:**
```bash
# Should show 8 freight_db.public.* topics + 3 mz.* sink topics
docker exec redpanda rpk topic list

# Materialize views
psql -h localhost -p 6875 -U materialize -c "SELECT * FROM v_active_shipments;"
psql -h localhost -p 6875 -U materialize -c "SELECT * FROM v_job_summary;"
```

---

## Services & Ports

| Service | Port | Description |
|---|---|---|
| PostgreSQL | `5432` | Source database |
| Debezium | `8083` | Kafka Connect REST API |
| Redpanda | `19092` | Kafka-compatible broker (external) |
| Redpanda Console | `8080` | Topic browser UI |
| Materialize | `6875` | Streaming SQL (psql-compatible) |
| FastAPI | `8000` | REST API (`/docs` for Swagger) |
| Streamlit | `8501` | Live tracking dashboard |

---

## API Endpoints

All entities support full CRUD. Base URL: `http://localhost:8000`

| Method | Path | Description |
|---|---|---|
| GET | `/locations/` | List all locations |
| GET | `/vehicles/` | List all vehicles |
| GET | `/freights/` | List all freight items |
| GET | `/purchase-orders/` | List purchase orders |
| GET | `/shipments/` | List shipments |
| GET | `/jobs/` | List jobs |
| GET | `/invoices/` | List invoices |
| GET | `/tracking/` | Recent tracking events |
| GET | `/tracking/vehicle/{id}` | Hop trail for a vehicle |

All `GET /` endpoints support `POST /`, `PUT /{id}`, `DELETE /{id}`. See `/docs` for full schema.

---

## Dashboard Tabs

| Tab | Data source | What it shows |
|---|---|---|
| 🗺 Live Map | PostgreSQL | Latest vehicle positions; hop trail with speed colour scale |
| 📦 Shipments | Materialize | Shipment count by mode (air/water/road) and status |
| 💰 Revenue | Materialize + PostgreSQL | Revenue per route with location names |
| 🔧 Jobs | Materialize | Job status distribution (pending/in_progress/completed) |
| 📄 Invoices | Materialize | Invoice aging by status and value |

---

## Materialize Views

| View | Description |
|---|---|
| `v_shipments` | Current state of all shipments |
| `v_jobs` | Current state of all jobs |
| `v_invoices` | Current state of all invoices |
| `v_active_shipments` | Shipment count grouped by mode + status |
| `v_revenue_by_route` | Revenue and order count per origin→destination route |
| `v_job_summary` | Job count grouped by status |
| `v_invoice_aging` | Invoice count and value grouped by payment status |

Sinks publish `v_active_shipments`, `v_revenue_by_route`, and `v_job_summary` back to Redpanda topics (`mz.*`).

---

## Stopping & Cleanup

```bash
# Stop (preserves data volumes)
docker compose down

# Full reset — wipes all data
docker compose down -v
```

---

## Project Structure

```
freight-cdc/
├── docker-compose.yml          # All services
├── .env                        # DB credentials
├── postgres/
│   └── init.sql                # Schema, indexes, publication, seed data
├── debezium/
│   ├── freight-connector.json  # Debezium PostgreSQL connector config
│   └── register-connector.sh  # Auto-registers connector on startup
├── materialize/
│   └── setup.sql               # Kafka sources, materialized views, sinks
├── generator/
│   └── generate.py             # Continuous data generator (psycopg2)
├── consumer/
│   └── consumer.py             # Kafka consumer for Materialize sink topics
├── api/
│   ├── main.py                 # FastAPI application
│   ├── database.py             # PostgreSQL connection
│   ├── schemas.py              # Pydantic request/response models
│   └── routers/                # One router per entity (8 total)
├── dashboard/
    └── app.py                  # Streamlit real-time dashboard
```